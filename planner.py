import json
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from config import settings
from schemas import ALL_TOOLS

client = OpenAI(api_key=settings.openai_api_key)

_PROMPT_TEMPLATE = Path("prompts/planner.txt").read_text()


class PlanStep(BaseModel):
    tool: str
    args: dict = Field(default_factory=dict)
    purpose: str


class Plan(BaseModel):
    steps: list[PlanStep] = Field(..., min_length=1)


class PlanError(Exception):
    pass


def _tool_listing() -> str:
    lines = []
    for schema in ALL_TOOLS:
        fn = schema["function"]
        params = ", ".join(fn["parameters"].get("properties", {}).keys())
        lines.append(f"- {fn['name']}({params}): {fn['description']}")
    return "\n".join(lines)


def _registered_tool_names() -> set[str]:
    return {schema["function"]["name"] for schema in ALL_TOOLS}


def generate_plan(request: str) -> Plan:
    system_prompt = _PROMPT_TEMPLATE.replace("<<TOOL_LISTING>>", _tool_listing())

    chat = client.chat.completions.create(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request},
        ],
        response_format={"type": "json_object"},
    )

    try:
        raw = json.loads(chat.choices[0].message.content)
        plan = Plan(**raw)
    except (json.JSONDecodeError, ValidationError) as e:
        raise PlanError(f"Planner produced an invalid plan: {e}")

    known = _registered_tool_names()
    for step in plan.steps:
        if step.tool not in known:
            raise PlanError(f"Plan references unknown tool: '{step.tool}'")

    return plan
