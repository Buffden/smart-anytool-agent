import json
from pathlib import Path
from unittest.mock import ANY, patch

from approval import ScriptedApprover
from config import settings
from planner import Plan
from workflow import run_workflow

_PLAN = Plan(steps=[{"tool": "calculator", "args": {"expression": "1+1"}, "purpose": "add"}])
_RESULTS = [{"purpose": "add", "tool": "calculator", "result": {"result": 2}}]
_OUTPUT = {"report": "The answer is 2.", "email_draft": "Hi, the answer is 2."}


def _run(results=_RESULTS, **kwargs):
    with patch("workflow.generate_plan", return_value=_PLAN):
        with patch("workflow.execute_plan", return_value=results) as mock_execute:
            with patch("workflow.synthesize", return_value=dict(_OUTPUT)) as mock_synth:
                output = run_workflow("what is 1 + 1?", **kwargs)
    return output, mock_execute, mock_synth


def _outbox() -> list[Path]:
    path = Path(settings.outbox_dir)
    return list(path.glob("*.eml")) if path.exists() else []


def _audit() -> list[dict]:
    path = Path(settings.audit_log_path)
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def test_run_workflow_wires_planner_executor_and_synthesis():
    output, mock_execute, mock_synth = _run()
    mock_execute.assert_called_once_with(_PLAN, stop_on_failure=True, approver=None, run_id=output["run_id"])
    mock_synth.assert_called_once_with("what is 1 + 1?", _RESULTS)
    assert output["report"] == "The answer is 2."


def test_run_workflow_passes_through_stop_on_failure_flag():
    _, mock_execute, _ = _run(stop_on_failure=False)
    mock_execute.assert_called_once_with(_PLAN, stop_on_failure=False, approver=None, run_id=ANY)


def test_no_recipient_means_no_send_proposed():
    output, _, _ = _run(approver=ScriptedApprover([True]))
    assert output["email"]["status"] == "not_proposed"
    assert _outbox() == []


def test_approved_send_creates_an_outbox_file():
    output, _, _ = _run(approver=ScriptedApprover([True]), recipient="ops@example.com")
    assert output["email"]["status"] == "sent"
    assert len(_outbox()) == 1
    assert "Hi, the answer is 2." in _outbox()[0].read_text()


def test_denied_send_creates_nothing_and_keeps_the_report():
    output, _, _ = _run(approver=ScriptedApprover([False]), recipient="ops@example.com")
    assert output["email"]["status"] == "not_sent"
    assert output["email"]["kind"] == "denied"
    assert output["report"] == "The answer is 2."
    assert _outbox() == []


def test_no_approver_sends_nothing():
    output, _, _ = _run(recipient="ops@example.com")
    assert output["email"]["kind"] == "denied"
    assert _outbox() == []


def test_approver_sees_the_real_recipient_and_body():
    approver = ScriptedApprover([False])
    _run(approver=approver, recipient="ops@example.com")
    [request] = approver.requests
    assert request.tool == "send_email"
    assert request.args["recipient"] == "ops@example.com"
    assert request.args["body"] == "Hi, the answer is 2."


def test_partial_failure_reaches_the_approval_request():
    results = [
        {"purpose": "count", "tool": "query_database", "result": {"rows": [{"n": 3}]}},
        {"purpose": "salaries", "tool": "query_database",
         "result": {"error": 'column "pay" does not exist', "kind": "syntax"}},
    ]
    approver = ScriptedApprover([False])
    _run(results=results, approver=approver, recipient="ops@example.com")
    assert approver.requests[0].failed_steps == [{
        "step": 2, "tool": "query_database", "purpose": "salaries",
        "error": 'column "pay" does not exist',
    }]


def test_send_is_audited_under_the_run_id():
    output, _, _ = _run(approver=ScriptedApprover([True]), recipient="ops@example.com")
    [record] = _audit()
    assert record["tool"] == "send_email"
    assert record["run_id"] == output["run_id"]
    assert record["decision"] == "approved"


# clarification fallback

from planner import Clarification


def test_clarification_is_returned_and_nothing_runs():
    approver = ScriptedApprover([True])
    with patch("workflow.generate_plan", return_value=Clarification(question="Which team?")):
        with patch("workflow.execute_plan") as mock_execute:
            with patch("workflow.synthesize") as mock_synth:
                output = run_workflow("send the report to the team", approver=approver, recipient="ops@example.com")

    assert output["clarification"] == "Which team?"
    mock_execute.assert_not_called()
    mock_synth.assert_not_called()
    assert approver.requests == []
    assert _outbox() == []
    assert _audit() == []
