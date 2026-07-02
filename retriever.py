import json
import logging
from pathlib import Path
from openai import OpenAI
from config import settings
from schemas import ALL_TOOLS, TOOL_CATEGORIES
import agent

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


def run(question: str) -> str:
    tools = filter_tools(question)

    for attempt in range(1, settings.retriever_max_retries + 1):
        result = agent.solve(question, tools)

        if result is not None:
            if attempt > 1:
                logger.info("self-reflection succeeded on attempt=%d", attempt)
            return result

        # widen tool selection on retry
        logger.warning("attempt=%d failed, widening to ALL_TOOLS for retry", attempt)
        tools = ALL_TOOLS

    return "I was unable to find an answer. Please try rephrasing your question."
