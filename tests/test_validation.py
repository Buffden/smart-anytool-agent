import json
from unittest.mock import patch

from approval import ScriptedApprover
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

def test_missing_required_arg_analyze_text():
    assert "error" in dispatch("analyze_text", '{}')

def test_missing_required_arg_classify_text():
    assert "error" in dispatch("classify_text", '{}')

def test_missing_required_arg_send_chat_message():
    assert "error" in dispatch("send_chat_message", '{}')

def test_missing_required_arg_get_chat_history():
    assert "error" in dispatch("get_chat_history", '{}')

def test_missing_required_arg_query_database():
    assert "error" in dispatch("query_database", '{}')

def test_query_database_rejects_empty_string():
    assert "error" in dispatch("query_database", json.dumps({"sql": ""}))

def test_query_database_rejects_overlong_sql():
    result = dispatch("query_database", json.dumps({"sql": "SELECT " + "x" * 2000}))
    assert "error" in result

def test_analyze_text_rejects_empty_string():
    assert "error" in dispatch("analyze_text", json.dumps({"text": ""}))

def test_analyze_text_rejects_overlong_text():
    result = dispatch("analyze_text", json.dumps({"text": "x" * 5001}))
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

def test_valid_analyze_text_call():
    with patch("tools.analyze_text", return_value={"summary": "..."}) as mock:
        result = dispatch("analyze_text", json.dumps({"text": "some text"}))
    mock.assert_called_once_with(text="some text")
    assert result["summary"] == "..."

def test_valid_send_chat_message_call_without_conversation_id():
    with patch("tools.send_chat_message", return_value={"conversationId": "abc-123"}) as mock:
        dispatch("send_chat_message", json.dumps({"message": "hi"}), approver=ScriptedApprover([True]))
    mock.assert_called_once_with(message="hi", conversation_id=None)

def test_valid_send_chat_message_call_with_conversation_id():
    with patch("tools.send_chat_message", return_value={"conversationId": "abc-123"}) as mock:
        dispatch(
            "send_chat_message",
            json.dumps({"message": "hi", "conversation_id": "abc-123"}),
            approver=ScriptedApprover([True]),
        )
    mock.assert_called_once_with(message="hi", conversation_id="abc-123")

def test_valid_list_conversations_call():
    with patch("tools.list_conversations", return_value=[]) as mock:
        result = dispatch("list_conversations", '{}')
    mock.assert_called_once_with()
    assert result == []

def test_valid_query_database_call():
    with patch("tools.query_database", return_value={"rows": [], "kind": "ok"}) as mock:
        result = dispatch("query_database", json.dumps({"sql": "SELECT 1"}))
    mock.assert_called_once_with(sql="SELECT 1")
    assert result["kind"] == "ok"


# error and success results have the same shape

def test_error_and_success_are_both_dicts():
    error_result = dispatch("get_weather", '{}')
    with patch("tools.get_weather", return_value={"temperature": 22}):
        success_result = dispatch("get_weather", json.dumps({"location": "Tokyo"}))
    assert isinstance(error_result, dict)
    assert isinstance(success_result, dict)


# risk classification

import pytest
import validation
from schemas import ALL_TOOLS

_EXPECTED_RISK = {
    "get_weather": "read",
    "web_search": "read",
    "calculator": "read",
    "analyze_text": "read",
    "classify_text": "read",
    "list_conversations": "read",
    "get_chat_history": "read",
    "query_database": "read",
    "send_chat_message": "write",
    "send_email": "write",
}

@pytest.mark.parametrize("schema", ALL_TOOLS, ids=lambda s: s["function"]["name"])
def test_every_schema_tool_has_an_explicit_classification(schema):
    name = schema["function"]["name"]
    entry = validation._REGISTRY[name]
    assert len(entry) == 3, f"{name} is registered without a risk classification"
    assert entry[2] in {validation.READ, validation.WRITE}
    assert entry[2] == _EXPECTED_RISK[name]

def test_registry_and_expected_table_cover_the_same_tools():
    assert set(validation._REGISTRY) == set(_EXPECTED_RISK)

def test_unclassified_tool_is_treated_as_write():
    with patch.dict(validation._REGISTRY, {"dummy": (validation.CalculatorArgs, "calculator")}):
        assert validation.classify("dummy") == validation.WRITE

def test_unknown_tool_is_treated_as_write():
    assert validation.classify("never_registered") == validation.WRITE
