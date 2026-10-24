import json
import logging
from openai import OpenAI
from approval import Approver
from config import settings
from validation import WRITE, classify, dispatch

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)

_BLOCKED_AFTER_DENIAL = {
    "error": (
        "Not attempted: a human already declined an action in this turn, so "
        "no further write actions are allowed. Tell the user what was declined."
    ),
    "kind": "denied",
}


def solve(
    question: str,
    tools: list[dict],
    approver: Approver | None = None,
    run_id: str | None = None,
) -> str | None:
    messages = [{"role": "user", "content": question}]
    # Once a human says no, the model can't route around it with another
    # write (e.g. send_chat_message after a declined send_email).
    write_denied = False

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
            if write_denied and classify(call.function.name) == WRITE:
                logger.warning("iteration=%d blocked write %r after a denial", iteration, call.function.name)
                result = _BLOCKED_AFTER_DENIAL
            else:
                result = dispatch(
                    call.function.name,
                    call.function.arguments,
                    approver=approver,
                    reason=f"Requested while answering: {question}",
                    run_id=run_id,
                )
                if isinstance(result, dict) and result.get("kind") == "denied":
                    write_denied = True
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    logger.warning("reached iteration limit of %d", settings.agent_max_iterations)
    return None
