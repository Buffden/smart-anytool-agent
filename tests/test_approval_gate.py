import time
from unittest.mock import patch

import validation
from approval import ApprovalRequest, Decision, ScriptedApprover
from validation import dispatch

_CHAT_ARGS = '{"message": "hello"}'


def test_read_skips_the_approver():
    approver = ScriptedApprover([False])
    result = dispatch("calculator", '{"expression": "1+1"}', approver=approver)
    assert result["result"] == 2
    assert approver.requests == []


def test_write_reaches_the_approver_with_args_and_reason():
    approver = ScriptedApprover([False])
    with patch("tools.send_chat_message") as mock_tool:
        dispatch("send_chat_message", _CHAT_ARGS, approver=approver, reason="say hi")
    mock_tool.assert_not_called()
    assert approver.requests == [
        ApprovalRequest(
            tool="send_chat_message",
            args={"message": "hello", "conversation_id": None},
            reason="say hi",
        )
    ]


def test_approved_write_runs_the_tool():
    with patch("tools.send_chat_message", return_value={"reply": "hi"}) as mock_tool:
        result = dispatch("send_chat_message", _CHAT_ARGS, approver=ScriptedApprover([True]))
    mock_tool.assert_called_once_with(message="hello", conversation_id=None)
    assert result == {"reply": "hi"}


def test_denied_write_does_not_run_the_tool():
    with patch("tools.send_chat_message") as mock_tool:
        result = dispatch("send_chat_message", _CHAT_ARGS, approver=ScriptedApprover([False]))
    mock_tool.assert_not_called()
    assert result["kind"] == "denied"
    assert result["decision"] == "denied"


def test_no_approver_denies():
    with patch("tools.send_chat_message") as mock_tool:
        result = dispatch("send_chat_message", _CHAT_ARGS)
    mock_tool.assert_not_called()
    assert result["kind"] == "denied"
    assert result["decision"] == "no_approver"


def test_approver_raising_denies():
    def broken(_request):
        raise RuntimeError("boom")

    with patch("tools.send_chat_message") as mock_tool:
        result = dispatch("send_chat_message", _CHAT_ARGS, approver=broken)
    mock_tool.assert_not_called()
    assert result["decision"] == "approver_error"


def test_approver_timeout_denies():
    def silent(_request):
        time.sleep(0.5)
        return Decision(approved=True, by="too-late")

    with patch.object(validation.settings, "approval_timeout_s", 0.05):
        with patch("tools.send_chat_message") as mock_tool:
            result = dispatch("send_chat_message", _CHAT_ARGS, approver=silent)
    mock_tool.assert_not_called()
    assert result["decision"] == "timeout"


def test_anything_but_an_explicit_yes_denies():
    for answer in ["yes", 1, None, {"approved": True}, Decision(approved="yes", by="x")]:
        with patch("tools.send_chat_message") as mock_tool:
            result = dispatch("send_chat_message", _CHAT_ARGS, approver=lambda _r, a=answer: a)
        mock_tool.assert_not_called()
        assert result["kind"] == "denied", answer


def test_unclassified_tool_goes_to_the_approver():
    approver = ScriptedApprover([False])
    with patch.dict(validation._REGISTRY, {"dummy": (validation.CalculatorArgs, "calculator")}):
        result = dispatch("dummy", '{"expression": "1+1"}', approver=approver)
    assert len(approver.requests) == 1
    assert result["kind"] == "denied"


def test_failed_steps_reach_the_approver():
    approver = ScriptedApprover([False])
    failed = [{"tool": "query_database", "error": "column does not exist"}]
    dispatch("send_chat_message", _CHAT_ARGS, approver=approver, failed_steps=failed)
    assert approver.requests[0].failed_steps == failed


def test_scripted_sequence_is_deterministic():
    for _ in range(3):
        approver = ScriptedApprover([True, False, True])
        with patch("tools.send_chat_message", return_value={"reply": "ok"}):
            kinds = [
                dispatch("send_chat_message", _CHAT_ARGS, approver=approver).get("kind", "ok")
                for _ in range(3)
            ]
        assert kinds == ["ok", "denied", "ok"]
