import json
from unittest.mock import MagicMock, patch

from retriever import filter_tools
from schemas import ALL_TOOLS, TOOL_CATEGORIES


# helpers

def make_openai_response(payload: dict) -> MagicMock:
    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# return type

def test_returns_a_list():
    mock = make_openai_response({"category": "computation", "reason": "math"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is 10 + 5?")
    assert isinstance(result, list)

def test_returns_list_of_dicts():
    mock = make_openai_response({"category": "computation", "reason": "math"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is 10 + 5?")
    assert all(isinstance(t, dict) for t in result)


# computation category

def test_math_question_returns_computation_tools():
    mock = make_openai_response({"category": "computation", "reason": "math"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is 15% of 340?")
    assert result == TOOL_CATEGORIES["computation"]

def test_computation_tools_exclude_weather():
    mock = make_openai_response({"category": "computation", "reason": "math"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is 2 ** 8?")
    names = [t["function"]["name"] for t in result]
    assert "get_weather" not in names

def test_computation_tools_exclude_web_search():
    mock = make_openai_response({"category": "computation", "reason": "math"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is 2 ** 8?")
    names = [t["function"]["name"] for t in result]
    assert "web_search" not in names

def test_computation_tools_include_calculator():
    mock = make_openai_response({"category": "computation", "reason": "math"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is 2 ** 8?")
    names = [t["function"]["name"] for t in result]
    assert "calculator" in names


# data_lookup category

def test_weather_question_returns_data_lookup_tools():
    mock = make_openai_response({"category": "data_lookup", "reason": "live weather"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is the weather in Tokyo?")
    assert result == TOOL_CATEGORIES["data_lookup"]

def test_data_lookup_tools_include_weather():
    mock = make_openai_response({"category": "data_lookup", "reason": "live weather"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is the weather in Tokyo?")
    names = [t["function"]["name"] for t in result]
    assert "get_weather" in names

def test_data_lookup_tools_include_web_search():
    mock = make_openai_response({"category": "data_lookup", "reason": "live search"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is the latest news about AI?")
    names = [t["function"]["name"] for t in result]
    assert "web_search" in names

def test_data_lookup_tools_exclude_calculator():
    mock = make_openai_response({"category": "data_lookup", "reason": "live weather"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is the weather in Tokyo?")
    names = [t["function"]["name"] for t in result]
    assert "calculator" not in names


# unknown category — fallback to ALL_TOOLS

def test_unknown_category_returns_all_tools():
    mock = make_openai_response({"category": "unknown", "reason": "spans both"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("What is 200 * 4 and the weather in Paris?")
    assert result == ALL_TOOLS

def test_unrecognised_category_returns_all_tools():
    mock = make_openai_response({"category": "something_else", "reason": "???"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("some question")
    assert result == ALL_TOOLS

def test_missing_category_key_returns_all_tools():
    mock = make_openai_response({"reason": "no category provided"})
    with patch("retriever.client.chat.completions.create", return_value=mock):
        result = filter_tools("some question")
    assert result == ALL_TOOLS


# failure cases

def test_openai_failure_returns_all_tools():
    with patch("retriever.client.chat.completions.create", side_effect=Exception("network error")):
        result = filter_tools("What is the weather in London?")
    assert result == ALL_TOOLS

def test_does_not_raise_on_failure():
    with patch("retriever.client.chat.completions.create", side_effect=Exception("unexpected")):
        result = filter_tools("some question")
    assert isinstance(result, list)

def test_openai_failure_result_is_non_empty():
    with patch("retriever.client.chat.completions.create", side_effect=Exception("timeout")):
        result = filter_tools("some question")
    assert len(result) > 0
