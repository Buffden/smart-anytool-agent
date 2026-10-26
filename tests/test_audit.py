import json
from pathlib import Path
from unittest.mock import patch

from approval import ScriptedApprover
from config import settings
from validation import dispatch


def _records() -> list[dict]:
    path = Path(settings.audit_log_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_read_is_recorded_with_approval_not_needed():
    dispatch("calculator", '{"expression": "2*3"}', run_id="run-a")
    [rec] = _records()
    assert rec["run_id"] == "run-a"
    assert rec["tool"] == "calculator"
    assert rec["risk"] == "read"
    assert rec["args"] == {"expression": "2*3"}
    assert rec["decision"] == "not_needed"
    assert rec["outcome"] == "success"


def test_result_is_not_logged():
    dispatch("calculator", '{"expression": "2*3"}')
    [rec] = _records()
    assert "result" not in rec
    assert 6 not in rec.values()


def test_approved_write_records_who_approved():
    with patch("tools.send_chat_message", return_value={"reply": "ok"}):
        dispatch("send_chat_message", '{"message": "hi"}', approver=ScriptedApprover([True], by="alice"))
    [rec] = _records()
    assert rec["risk"] == "write"
    assert rec["decision"] == "approved"
    assert rec["decided_by"] == "alice"
    assert rec["outcome"] == "success"


def test_denied_write_is_recorded():
    dispatch("send_chat_message", '{"message": "hi"}', approver=ScriptedApprover([False], by="bob"))
    [rec] = _records()
    assert rec["decision"] == "denied"
    assert rec["decided_by"] == "bob"
    assert rec["outcome"] == "denied"


def test_missing_approver_is_recorded():
    dispatch("send_chat_message", '{"message": "hi"}')
    [rec] = _records()
    assert rec["decision"] == "no_approver"


def test_validation_failures_are_recorded():
    dispatch("no_such_tool", "{}")
    dispatch("calculator", "not json")
    dispatch("calculator", "{}")
    recs = _records()
    assert [r["outcome"] for r in recs] == ["validation"] * 3
    assert recs[1]["args"] == "not json"


def test_one_record_per_call_sharing_a_run_id():
    approver = ScriptedApprover([True, False])
    with patch("tools.send_chat_message", return_value={"reply": "ok"}):
        dispatch("calculator", '{"expression": "1+1"}', run_id="r1")
        dispatch("send_chat_message", '{"message": "a"}', approver=approver, run_id="r1")
        dispatch("send_chat_message", '{"message": "b"}', approver=approver, run_id="r1")
    recs = _records()
    assert len(recs) == 3
    assert {r["run_id"] for r in recs} == {"r1"}
    assert [r["decision"] for r in recs] == ["not_needed", "approved", "denied"]


def test_log_is_only_appended_to():
    dispatch("calculator", '{"expression": "1"}')
    first = Path(settings.audit_log_path).read_text()
    dispatch("calculator", '{"expression": "2"}')
    second = Path(settings.audit_log_path).read_text()
    assert second.startswith(first)
    assert len(second.splitlines()) == 2


def test_tool_that_raises_is_still_recorded():
    with patch("tools.calculator", side_effect=RuntimeError("boom")):
        try:
            dispatch("calculator", '{"expression": "1"}')
        except RuntimeError:
            pass
    [rec] = _records()
    assert rec["outcome"] == "exception"
