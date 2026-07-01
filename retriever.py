import json
import logging
from pathlib import Path
from openai import OpenAI
from config import settings
from schemas import ALL_TOOLS, TOOL_CATEGORIES

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = Path("prompts/tool_filter.txt").read_text()


def filter_tools(question: str) -> list[dict]:
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
        category = data.get("category", "unknown")
        reason = data.get("reason", "")

        if category in TOOL_CATEGORIES:
            logger.info("tool filter selected category=%r reason=%r", category, reason)
            return TOOL_CATEGORIES[category]

        logger.info("tool filter fell back to ALL_TOOLS category=%r reason=%r", category, reason)
        return ALL_TOOLS

    except Exception:
        logger.warning("tool filter failed, falling back to ALL_TOOLS")
        return ALL_TOOLS
