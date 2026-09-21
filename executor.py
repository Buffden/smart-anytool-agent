import json
import re

from openai import OpenAI

from config import settings
from planner import Plan
from validation import dispatch

client = OpenAI(api_key=settings.openai_api_key)

# Not anchored to the whole string: a placeholder is usually embedded inside
# a larger value (e.g. a SQL fragment), not the entire argument by itself.
_REF_PATTERN = re.compile(r"\{\{step_(\d+)\.([^{}]+)\}\}")


def _resolve_placeholder(match: re.Match, results: list[dict]):
    step_num, path = match.group(1), match.group(2)
    index = int(step_num) - 1
    if index < 0 or index >= len(results):
        raise ValueError(f"step reference out of range: {match.group(0)}")

    current = results[index]["result"]
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise ValueError(
                f"cannot resolve '{match.group(0)}': reached a non-container at '{part}'"
            )

    return current


def _resolve_value(value, results: list[dict]):
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    full_match = _REF_PATTERN.fullmatch(stripped)
    if full_match:
        # The whole argument is one placeholder -- preserve the resolved
        # value's real type (e.g. an int id stays an int, not "9").
        return _resolve_placeholder(full_match, results)

    if not _REF_PATTERN.search(value):
        return value

    def substitute(match: re.Match) -> str:
        return str(_resolve_placeholder(match, results))

    return _REF_PATTERN.sub(substitute, value)


def _resolve_args(args: dict, results: list[dict]) -> dict:
    return {key: _resolve_value(value, results) for key, value in args.items()}


def execute_plan(plan: Plan, stop_on_failure: bool = True) -> list[dict]:
    results = []

    for step in plan.steps:
        try:
            resolved_args = _resolve_args(step.args, results)
        except (ValueError, IndexError, KeyError, TypeError) as e:
            result = {"error": f"Could not resolve step arguments: {e}", "kind": "blocked"}
            results.append({"purpose": step.purpose, "tool": step.tool, "result": result})
            if stop_on_failure:
                break
            continue

        result = dispatch(step.tool, json.dumps(resolved_args))
        results.append({"purpose": step.purpose, "tool": step.tool, "result": result})

        if isinstance(result, dict) and "error" in result and stop_on_failure:
            break

    return results


_SYNTHESIS_PROMPT = (
    "You are the final step of a multi-step workflow. You are given the "
    "original request and the results of every step that ran, in order. "
    "Write two things: a short report answering the request, and a short "
    "follow-up email draft summarizing it for a colleague. If any step's "
    "result contains an \"error\" key, say plainly what you couldn't "
    "determine because of it -- never fill the gap with a plausible-"
    "sounding guess. Respond with JSON only: "
    '{"report": "...", "email_draft": "..."}'
)


def synthesize(request: str, results: list[dict]) -> dict:
    chat = client.chat.completions.create(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        messages=[
            {"role": "system", "content": _SYNTHESIS_PROMPT},
            {
                "role": "user",
                "content": json.dumps({"request": request, "step_results": results}),
            },
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(chat.choices[0].message.content)
