import json
from unittest.mock import patch

from validation import dispatch


# dispatch unknown tool

def test_unknown_tool_returns_error():
    result = dispatch("nonexistent_tool", '{}')
    assert "error" in result
    assert "nonexistent_tool" in result["error"]


# dispatch malformed JSON

def test_malformed_json_returns_error():
    result = dispatch("get_weather", "{location: Tokyo}")
    assert isinstance(result, dict)
    assert "error" in result

def test_malformed_json_does_not_raise():
    result = dispatch("calculator", "not json at all")
    assert isinstance(result, dict)
    assert "error" in result


# dispatch missing required arguments

def test_missing_required_arg_weather():
    result = dispatch("get_weather", '{}')
    assert "error" in result

def test_missing_required_arg_web_search():
    result = dispatch("web_search", '{}')
    assert "error" in result

def test_missing_required_arg_calculator():
    result = dispatch("calculator", '{}')
    assert "error" in result


# dispatch wrong argument types

def test_wrong_type_num_results():
    result = dispatch("web_search", json.dumps({"query": "test", "num_results": "five"}))
    assert "error" in result

def test_invalid_enum_unit():
    result = dispatch("get_weather", json.dumps({"location": "Tokyo", "unit": "kelvin"}))
    assert "error" in result

def test_num_results_out_of_range_rejected():
    assert "error" in dispatch("web_search", json.dumps({"query": "test", "num_results": 0}))
    assert "error" in dispatch("web_search", json.dumps({"query": "test", "num_results": -1}))


# dispatch valid calls routed to correct tool

def test_valid_weather_call():
    with patch("tools.get_weather", return_value={"temperature": 22}) as mock:
        result = dispatch("get_weather", json.dumps({"location": "Tokyo"}))
    mock.assert_called_once_with(location="Tokyo", unit="celsius")
    assert result["temperature"] == 22

def test_valid_weather_with_unit():
    with patch("tools.get_weather", return_value={"temperature": 72}) as mock:
        dispatch("get_weather", json.dumps({"location": "London", "unit": "fahrenheit"}))
    mock.assert_called_once_with(location="London", unit="fahrenheit")

def test_valid_web_search_call():
    with patch("tools.web_search", return_value=[{"title": "r"}]) as mock:
        result = dispatch("web_search", json.dumps({"query": "AI news", "num_results": 3}))
    mock.assert_called_once_with(query="AI news", num_results=3)
    assert isinstance(result, list)

def test_valid_calculator_call():
    with patch("tools.calculator", return_value={"expression": "2+2", "result": 4}) as mock:
        result = dispatch("calculator", json.dumps({"expression": "2+2"}))
    mock.assert_called_once_with(expression="2+2")
    assert result["result"] == 4


# error and success results have the same shape

def test_error_and_success_are_both_dicts():
    error_result = dispatch("get_weather", '{}')
    with patch("tools.get_weather", return_value={"temperature": 22}):
        success_result = dispatch("get_weather", json.dumps({"location": "Tokyo"}))
    assert isinstance(error_result, dict)
    assert isinstance(success_result, dict)
