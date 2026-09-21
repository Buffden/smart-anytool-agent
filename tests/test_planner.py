import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from planner import Plan, PlanError, PlanStep, generate_plan


def make_openai_response(payload) -> MagicMock:
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# Plan / PlanStep models

def test_plan_step_requires_tool_and_purpose():
    with pytest.raises(ValidationError):
        PlanStep(args={})


def test_plan_step_args_default_to_empty_dict():
    step = PlanStep(tool="calculator", purpose="do math")
    assert step.args == {}


def test_plan_requires_at_least_one_step():
    with pytest.raises(ValidationError):
        Plan(steps=[])


def test_plan_accepts_valid_steps():
    plan = Plan(steps=[{"tool": "calculator", "args": {"expression": "1+1"}, "purpose": "add"}])
    assert len(plan.steps) == 1


# generate_plan

def test_generate_plan_returns_plan_for_valid_response():
    payload = {"steps": [{"tool": "calculator", "args": {"expression": "2+2"}, "purpose": "add numbers"}]}
    with patch("planner.client.chat.completions.create", return_value=make_openai_response(payload)):
        plan = generate_plan("what is 2 + 2?")
    assert isinstance(plan, Plan)
    assert plan.steps[0].tool == "calculator"


def test_generate_plan_rejects_empty_steps():
    with patch("planner.client.chat.completions.create", return_value=make_openai_response({"steps": []})):
        with pytest.raises(PlanError):
            generate_plan("some request")


def test_generate_plan_rejects_unknown_tool():
    payload = {"steps": [{"tool": "delete_everything", "args": {}, "purpose": "nope"}]}
    with patch("planner.client.chat.completions.create", return_value=make_openai_response(payload)):
        with pytest.raises(PlanError):
            generate_plan("some request")


def test_generate_plan_rejects_malformed_json():
    message = MagicMock()
    message.content = "not json at all"
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]

    with patch("planner.client.chat.completions.create", return_value=response):
        with pytest.raises(PlanError):
            generate_plan("some request")


def test_generate_plan_accepts_step_referencing_earlier_result():
    payload = {
        "steps": [
            {"tool": "query_database", "args": {"sql": "SELECT id FROM departments LIMIT 1"}, "purpose": "find dept"},
            {"tool": "query_database", "args": {"sql": "SELECT * FROM employees WHERE department_id = {{step_1.rows.0.id}}"}, "purpose": "list employees"},
        ]
    }
    with patch("planner.client.chat.completions.create", return_value=make_openai_response(payload)):
        plan = generate_plan("find the top department and list its employees")
    assert "{{step_1.rows.0.id}}" in plan.steps[1].args["sql"]
