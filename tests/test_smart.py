import json
from unittest.mock import MagicMock, patch

from smart import self_awareness_check


# helpers

def make_openai_response(payload: dict) -> MagicMock:
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# return structure

def test_returns_needs_tool_key():
    mock = make_openai_response({"needs_tool": False, "answer": "Paris", "reason": "stable fact"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the capital of France?")
    assert "needs_tool" in result

def test_returns_answer_key():
    mock = make_openai_response({"needs_tool": False, "answer": "Paris", "reason": "stable fact"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the capital of France?")
    assert "answer" in result

def test_returns_reason_key():
    mock = make_openai_response({"needs_tool": False, "answer": "Paris", "reason": "stable fact"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the capital of France?")
    assert "reason" in result

def test_needs_tool_is_bool():
    mock = make_openai_response({"needs_tool": False, "answer": "Paris", "reason": "stable fact"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the capital of France?")
    assert isinstance(result["needs_tool"], bool)


# no tool needed

def test_stable_fact_returns_no_tool():
    mock = make_openai_response({"needs_tool": False, "answer": "Paris", "reason": "stable fact"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the capital of France?")
    assert result["needs_tool"] is False

def test_stable_fact_returns_answer():
    mock = make_openai_response({"needs_tool": False, "answer": "Paris", "reason": "stable fact"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the capital of France?")
    assert result["answer"] == "Paris"


# tool needed

def test_weather_requires_tool():
    mock = make_openai_response({"needs_tool": True, "answer": None, "reason": "real-time data"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the weather in Tokyo?")
    assert result["needs_tool"] is True

def test_weather_answer_is_none():
    mock = make_openai_response({"needs_tool": True, "answer": None, "reason": "real-time data"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the weather in Tokyo?")
    assert result["answer"] is None

def test_calculation_requires_tool():
    mock = make_openai_response({"needs_tool": True, "answer": None, "reason": "calculation required"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is 15% of 340?")
    assert result["needs_tool"] is True

def test_recent_news_requires_tool():
    mock = make_openai_response({"needs_tool": True, "answer": None, "reason": "requires live search"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("What is the latest news about AI?")
    assert result["needs_tool"] is True


# missing keys in model response — safe defaults

def test_missing_needs_tool_defaults_to_true():
    mock = make_openai_response({"answer": None, "reason": "something"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("some question")
    assert result["needs_tool"] is True

def test_missing_reason_defaults_to_empty_string():
    mock = make_openai_response({"needs_tool": False, "answer": "yes"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("some question")
    assert result["reason"] == ""

def test_missing_answer_defaults_to_none():
    mock = make_openai_response({"needs_tool": True, "reason": "needs search"})
    with patch("smart.client.chat.completions.create", return_value=mock):
        result = self_awareness_check("some question")
    assert result["answer"] is None


# failure cases

def test_openai_failure_defaults_to_needs_tool():
    with patch("smart.client.chat.completions.create", side_effect=Exception("network error")):
        result = self_awareness_check("What is the capital of France?")
    assert result["needs_tool"] is True

def test_openai_failure_answer_is_none():
    with patch("smart.client.chat.completions.create", side_effect=Exception("network error")):
        result = self_awareness_check("What is the capital of France?")
    assert result["answer"] is None

def test_does_not_raise_on_failure():
    with patch("smart.client.chat.completions.create", side_effect=Exception("unexpected")):
        result = self_awareness_check("some question")
    assert isinstance(result, dict)
