import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Literal
from pydantic import BaseModel, ValidationError, Field
import audit
import tools as _tools
from approval import ApprovalRequest, Approver, Decision
from config import settings

# data contracts / validators

class GetWeatherArgs(BaseModel):
    location: str
    unit: Literal["celsius", "fahrenheit"] = settings.weather_default_unit


class WebSearchArgs(BaseModel):
    query: str
    num_results: int = Field(default=settings.web_search_default_results, gt=0)


class CalculatorArgs(BaseModel):
    expression: str


class AnalyzeTextArgs(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class ClassifyTextArgs(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class SendChatMessageArgs(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None


class ListConversationsArgs(BaseModel):
    pass


class GetChatHistoryArgs(BaseModel):
    conversation_id: str


class QueryDatabaseArgs(BaseModel):
    sql: str = Field(..., min_length=1, max_length=2000)


READ = "read"
WRITE = "write"

# (validator, function name, risk). Risk is by effect, not HTTP method:
# analyze_text POSTs but only computes; send_chat_message stores a message.
_REGISTRY: dict[str, tuple] = {
    "get_weather": (GetWeatherArgs, "get_weather", READ),
    "web_search":  (WebSearchArgs,  "web_search", READ),
    "calculator":  (CalculatorArgs, "calculator", READ),
    "analyze_text": (AnalyzeTextArgs, "analyze_text", READ),
    "classify_text": (ClassifyTextArgs, "classify_text", READ),
    "send_chat_message": (SendChatMessageArgs, "send_chat_message", WRITE),
    "list_conversations": (ListConversationsArgs, "list_conversations", READ),
    "get_chat_history": (GetChatHistoryArgs, "get_chat_history", READ),
    "query_database": (QueryDatabaseArgs, "query_database", READ),
}


def classify(tool_name: str) -> str:
    # Anything without an explicit "read" is a write, so a tool registered
    # without a classification gets gated instead of slipping through.
    entry = _REGISTRY.get(tool_name, ())
    if len(entry) >= 3 and entry[2] == READ:
        return READ
    return WRITE


_DENIED_MESSAGE = (
    "A human declined this action. The decision is final: do not retry it, "
    "rephrase it, or use another tool to get the same effect. Tell the user "
    "it was declined."
)


def _ask_approver(approver: Approver | None, request: ApprovalRequest) -> tuple[str, str | None]:
    # Every path except an explicit Decision(approved=True) is a denial.
    if approver is None:
        return "no_approver", None

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        decision = pool.submit(approver, request).result(timeout=settings.approval_timeout_s)
    except FutureTimeout:
        return "timeout", None
    except Exception:
        return "approver_error", None
    finally:
        # Don't wait on an approver that never answers.
        pool.shutdown(wait=False)

    if isinstance(decision, Decision) and decision.approved is True:
        return "approved", decision.by
    return "denied", getattr(decision, "by", None)


def dispatch(
    tool_name: str,
    raw_args: str,
    approver: Approver | None = None,
    reason: str = "",
    failed_steps: list[dict] | None = None,
    run_id: str | None = None,
) -> dict:
    risk = classify(tool_name)
    args = raw_args
    decision, decided_by = "not_needed", None
    result = None

    try:
        result, args, decision, decided_by = _gated_call(
            tool_name, raw_args, approver, reason, failed_steps
        )
        return result
    finally:
        # Lives here, not in the callers, so no path through dispatch skips it.
        audit.record(
            run_id=run_id,
            tool=tool_name,
            risk=risk,
            args=args,
            decision=decision,
            decided_by=decided_by,
            outcome=audit.outcome_of(result) if result is not None else "exception",
        )


def _gated_call(tool_name, raw_args, approver, reason, failed_steps):
    # Returns (result, args as logged, decision, decided_by).

    # Is the tool name known?
    if tool_name not in _REGISTRY:
        return {"error": f"Unknown tool: '{tool_name}'", "kind": "validation"}, raw_args, "not_needed", None

    # Is the JSON valid?
    try:
        args_dict = json.loads(raw_args)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON arguments: {e}", "kind": "validation"}, raw_args, "not_needed", None

    validator, fn_name = _REGISTRY[tool_name][:2]

    # are the arguments valid?
    try:
        validated = validator(**args_dict)
    except ValidationError as e:
        return {"error": f"Argument validation failed: {e}", "kind": "validation"}, args_dict, "not_needed", None

    args = validated.model_dump()
    decision, decided_by = "not_needed", None

    # approval gate: reads pass, writes need an explicit yes
    if classify(tool_name) == WRITE:
        request = ApprovalRequest(
            tool=tool_name,
            args=args,
            reason=reason,
            failed_steps=failed_steps or [],
        )
        decision, decided_by = _ask_approver(approver, request)
        if decision != "approved":
            return {"error": _DENIED_MESSAGE, "kind": "denied", "decision": decision}, args, decision, decided_by

    # calling the actual function now
    fn = getattr(_tools, fn_name)
    return fn(**args), args, decision, decided_by
