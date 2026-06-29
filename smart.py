import json
from pathlib import Path
from openai import OpenAI
from config import settings

client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = Path("prompts/self_awareness.txt").read_text()

def self_awareness_check(question: str) -> dict:
    try:
        chat = client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(chat.choices[0].message.content)
        return {
            "needs_tool": bool(data.get("needs_tool", True)),
            "answer": data.get("answer"),
            "reason": data.get("reason", ""),
        }

    except Exception:
        return {"needs_tool": True, "answer": None, "reason": "self-awareness check failed, defaulting to tool pipeline"}
