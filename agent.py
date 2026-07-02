import json
import logging
from openai import OpenAI
from config import settings
from validation import dispatch

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)


def solve(question: str, tools: list[dict]) -> str | None:
    messages = [{"role": "user", "content": question}]

    for iteration in range(1, settings.agent_max_iterations + 1):
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            messages=messages,
            tools=tools,
        )

        message = response.choices[0].message

        # no tool calls model produced a final answer
        if not message.tool_calls:
            logger.info("iteration=%d no tool calls, returning answer", iteration)
            return message.content

        # append assistant message with tool calls to conversation
        messages.append(message)

        # execute every tool call and append results before next iteration
        for call in message.tool_calls:
            logger.info(
                "iteration=%d tool=%r args=%r",
                iteration,
                call.function.name,
                call.function.arguments,
            )
            result = dispatch(call.function.name, call.function.arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    logger.warning("reached iteration limit of %d", settings.agent_max_iterations)
    return None
