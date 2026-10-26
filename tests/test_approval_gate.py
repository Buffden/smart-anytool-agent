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


# CLI approver

from approval import CliApprover


def _cli(answer):
    printed = []
    approver = CliApprover(input_fn=lambda _prompt: answer, print_fn=printed.append)
    return approver, printed


def test_cli_approver_yes_approves():
    approver, _ = _cli("yes")
    decision = approver(ApprovalRequest(tool="send_email", args={"recipient": "a@b.co"}))
    assert decision.approved is True
    assert decision.by.startswith("cli:")


def test_cli_approver_anything_else_declines():
    for answer in ["y", "no", "", "YES please", "ok"]:
        approver, _ = _cli(answer)
        assert approver(ApprovalRequest(tool="send_email", args={})).approved is False


def test_cli_approver_accepts_yes_with_whitespace_and_case():
    approver, _ = _cli("  Yes \n")
    assert approver(ApprovalRequest(tool="send_email", args={})).approved is True


def test_cli_approver_shows_failed_steps_before_the_action():
    approver, printed = _cli("no")
    approver(ApprovalRequest(
        tool="send_email",
        args={"recipient": "ops@example.com", "body": "report"},
        reason="send it",
        failed_steps=[{"step": 2, "tool": "query_database", "purpose": "salaries", "error": "bad column"}],
    ))
    text = "\n".join(printed)
    assert text.index("bad column") < text.index("Action: send_email")
    assert "ops@example.com" in text
    assert "send it" in text
