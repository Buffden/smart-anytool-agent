"""Graders for the SMART paper benchmarks.

Mirrors the paper's evaluate/inference_eval_{math,time}.py: try a cheap
match first, and only ask an LLM judge (gpt-4o, the paper's judge prompts)
when that fails. Each grader returns (correct, method), where method is
"numeric", "exact", "judge" or "unparsed".
"""
import re

from harness import ROOT, uncounted  # first: puts the project root on sys.path

from openai import OpenAI  # noqa: E402

from config import settings  # noqa: E402

client = OpenAI(api_key=settings.openai_api_key)

JUDGE_PROMPTS = {
    "math": (ROOT / "prompts" / "judge_math.txt").read_text(),
    "time": (ROOT / "prompts" / "judge_time.txt").read_text(),
}
USER_PROMPT = "- Model response: {answer}\n- Ground truth: {gold}\n- Judgment: "

NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def last_number(text: str) -> float | None:
    matches = NUMBER.findall(text or "")
    if not matches:
        return None
    try:
        return float(matches[-1].replace(",", ""))
    except ValueError:
        return None


def judge(kind: str, answer: str, gold: str, model: str) -> bool | None:
    with uncounted():
        chat = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": JUDGE_PROMPTS[kind]},
                {"role": "user", "content": USER_PROMPT.format(answer=answer, gold=gold)},
            ],
        )
    verdict = chat.choices[0].message.content.strip().lower()
    if verdict.startswith("correct"):
        return True
    if verdict.startswith("wrong"):
        return False
    return None


def grade_gsm8k(answer: str, gold: str, judge_model: str) -> tuple[bool | None, str]:
    flat = (answer or "").replace("\n", " ").strip()
    predicted = last_number(flat)
    if predicted is not None and abs(predicted - float(gold.replace(",", ""))) < 1e-6:
        return True, "numeric"
    verdict = judge("math", flat, gold, judge_model)
    return verdict, "judge" if verdict is not None else "unparsed"


def grade_freshqa(answer: str, gold: str, judge_model: str) -> tuple[bool | None, str]:
    flat = (answer or "").replace("\n", " ").strip()
    if flat.lower() == gold.lower():
        return True, "exact"
    verdict = judge("time", flat, gold, judge_model)
    return verdict, "judge" if verdict is not None else "unparsed"


GRADERS = {"gsm8k": grade_gsm8k, "freshqa": grade_freshqa}
