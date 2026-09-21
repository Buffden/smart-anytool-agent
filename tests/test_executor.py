import json
from unittest.mock import MagicMock, patch

import pytest

from executor import _resolve_args, _resolve_value, execute_plan, synthesize
from planner import Plan


def make_openai_response(payload) -> MagicMock:
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# _resolve_value

def test_resolve_value_passes_through_non_placeholder_strings():
    assert _resolve_value("plain string", []) == "plain string"


def test_resolve_value_passes_through_non_string_values():
    assert _resolve_value(42, []) == 42


def test_resolve_value_walks_dict_and_list_path():
    results = [{"purpose": "p", "tool": "t", "result": {"rows": [{"id": 7}]}}]
    assert _resolve_value("{{step_1.rows.0.id}}", results) == 7


def test_resolve_value_out_of_range_step_raises():
    with pytest.raises(ValueError):
        _resolve_value("{{step_2.rows.0.id}}", [{"result": {"rows": []}}])


def test_resolve_value_non_container_path_raises():
    results = [{"result": {"count": 5}}]
    with pytest.raises(ValueError):
        _resolve_value("{{step_1.count.nested}}", results)


def test_resolve_args_only_substitutes_matching_values():
    results = [{"result": {"rows": [{"id": 3}]}}]
    resolved = _resolve_args({"sql": "x = {{step_1.rows.0.id}}", "note": "unchanged"}, results)
    assert resolved == {"sql": "x = 3", "note": "unchanged"}


# execute_plan

def test_execute_plan_runs_all_steps_and_accumulates_results():
    plan = Plan(steps=[
        {"tool": "calculator", "args": {"expression": "1+1"}, "purpose": "add"},
        {"tool": "calculator", "args": {"expression": "2+2"}, "purpose": "add more"},
    ])
    with patch("executor.dispatch", side_effect=[{"result": 2}, {"result": 4}]) as mock_dispatch:
        results = execute_plan(plan)

    assert len(results) == 2
    assert mock_dispatch.call_count == 2
    assert results[0]["result"] == {"result": 2}
    assert results[1]["result"] == {"result": 4}


def test_execute_plan_stops_on_failure_by_default():
    plan = Plan(steps=[
        {"tool": "calculator", "args": {"expression": "bad"}, "purpose": "fails"},
        {"tool": "calculator", "args": {"expression": "1+1"}, "purpose": "never runs"},
    ])
    with patch("executor.dispatch", side_effect=[{"error": "invalid", "kind": "blocked"}]) as mock_dispatch:
        results = execute_plan(plan)

    assert len(results) == 1
    assert mock_dispatch.call_count == 1


def test_execute_plan_continues_past_failure_when_told_to():
    plan = Plan(steps=[
        {"tool": "calculator", "args": {"expression": "bad"}, "purpose": "fails"},
        {"tool": "calculator", "args": {"expression": "1+1"}, "purpose": "still runs"},
    ])
    with patch("executor.dispatch", side_effect=[{"error": "invalid", "kind": "blocked"}, {"result": 2}]):
        results = execute_plan(plan, stop_on_failure=False)

    assert len(results) == 2
    assert "error" in results[0]["result"]
    assert results[1]["result"] == {"result": 2}


def test_execute_plan_unresolvable_reference_is_recorded_as_blocked():
    plan = Plan(steps=[
        {"tool": "calculator", "args": {"expression": "{{step_1.missing}}"}, "purpose": "bad ref"},
    ])
    with patch("executor.dispatch") as mock_dispatch:
        results = execute_plan(plan)

    mock_dispatch.assert_not_called()
    assert results[0]["result"]["kind"] == "blocked"


def test_execute_plan_resolves_dependency_before_dispatch():
    plan = Plan(steps=[
        {"tool": "query_database", "args": {"sql": "SELECT id FROM departments LIMIT 1"}, "purpose": "find dept"},
        {"tool": "query_database", "args": {"sql": "id={{step_1.rows.0.id}}"}, "purpose": "use it"},
    ])
    with patch(
        "executor.dispatch",
        side_effect=[{"rows": [{"id": 9}], "kind": "ok"}, {"rows": [], "kind": "empty"}],
    ) as mock_dispatch:
        execute_plan(plan)

    second_call_args = json.loads(mock_dispatch.call_args_list[1].args[1])
    assert second_call_args["sql"] == "id=9"


# synthesize

def test_synthesize_returns_report_and_email():
    payload = {"report": "All good.", "email_draft": "Hi team, ..."}
    with patch("executor.client.chat.completions.create", return_value=make_openai_response(payload)):
        result = synthesize("some request", [{"purpose": "p", "tool": "t", "result": {"rows": []}}])

    assert result == payload
