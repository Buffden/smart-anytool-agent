from unittest.mock import patch

from planner import Plan
from workflow import run_workflow


def test_run_workflow_wires_planner_executor_and_synthesis():
    fake_plan = Plan(steps=[{"tool": "calculator", "args": {"expression": "1+1"}, "purpose": "add"}])
    fake_results = [{"purpose": "add", "tool": "calculator", "result": {"result": 2}}]
    fake_output = {"report": "The answer is 2.", "email_draft": "Hi, the answer is 2."}

    with patch("workflow.generate_plan", return_value=fake_plan) as mock_plan:
        with patch("workflow.execute_plan", return_value=fake_results) as mock_execute:
            with patch("workflow.synthesize", return_value=fake_output) as mock_synth:
                result = run_workflow("what is 1 + 1?")

    mock_plan.assert_called_once_with("what is 1 + 1?")
    mock_execute.assert_called_once_with(fake_plan, stop_on_failure=True)
    mock_synth.assert_called_once_with("what is 1 + 1?", fake_results)
    assert result == fake_output


def test_run_workflow_passes_through_stop_on_failure_flag():
    fake_plan = Plan(steps=[{"tool": "calculator", "args": {}, "purpose": "x"}])
    with patch("workflow.generate_plan", return_value=fake_plan):
        with patch("workflow.execute_plan", return_value=[]) as mock_execute:
            with patch("workflow.synthesize", return_value={}):
                run_workflow("request", stop_on_failure=False)

    mock_execute.assert_called_once_with(fake_plan, stop_on_failure=False)
