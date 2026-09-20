import pytest
from schemas import (
    ALL_TOOLS,
    ANALYZE_TEXT_SCHEMA,
    CALCULATOR_SCHEMA,
    CLASSIFY_TEXT_SCHEMA,
    GET_CHAT_HISTORY_SCHEMA,
    LIST_CONVERSATIONS_SCHEMA,
    SEND_CHAT_MESSAGE_SCHEMA,
    TOOL_CATEGORIES,
    WEATHER_SCHEMA,
    WEB_SEARCH_SCHEMA,
)

# Helpers

def get_params(schema: dict) -> dict:
    return schema["function"]["parameters"]

def get_required(schema: dict) -> list:
    return get_params(schema)["required"]

def get_properties(schema: dict) -> dict:
    return get_params(schema)["properties"]

# Structure: every schema must have type / function / name / description

@pytest.mark.parametrize("schema", [WEATHER_SCHEMA, CALCULATOR_SCHEMA, WEB_SEARCH_SCHEMA])
def test_schema_top_level_type(schema):
    assert schema["type"] == "function"

@pytest.mark.parametrize("schema", [WEATHER_SCHEMA, CALCULATOR_SCHEMA, WEB_SEARCH_SCHEMA])
def test_schema_has_name_and_description(schema):
    fn = schema["function"]
    assert "name" in fn and fn["name"]
    assert "description" in fn and fn["description"]

@pytest.mark.parametrize("schema", [WEATHER_SCHEMA, CALCULATOR_SCHEMA, WEB_SEARCH_SCHEMA])
def test_schema_parameters_type_object(schema):
    assert get_params(schema)["type"] == "object"

# Weather schema

def test_weather_schema_name():
    assert WEATHER_SCHEMA["function"]["name"] == "get_weather"

def test_weather_required_fields():
    assert get_required(WEATHER_SCHEMA) == ["location"]

def test_weather_unit_is_optional():
    assert "unit" not in get_required(WEATHER_SCHEMA)

def test_weather_unit_enum():
    unit = get_properties(WEATHER_SCHEMA)["unit"]
    assert set(unit["enum"]) == {"celsius", "fahrenheit"}

def test_weather_description_covers_when_to_use():
    desc = WEATHER_SCHEMA["function"]["description"]
    assert "weather" in desc.lower()
    assert "do not" in desc.lower()

# Calculator schema

def test_calculator_schema_name():
    assert CALCULATOR_SCHEMA["function"]["name"] == "calculator"

def test_calculator_required_fields():
    assert get_required(CALCULATOR_SCHEMA) == ["expression"]

def test_calculator_description_covers_when_to_use():
    desc = CALCULATOR_SCHEMA["function"]["description"]
    assert "calculat" in desc.lower()
    assert "do not" in desc.lower()

# Web search schema

def test_web_search_schema_name():
    assert WEB_SEARCH_SCHEMA["function"]["name"] == "web_search"

def test_web_search_required_fields():
    assert get_required(WEB_SEARCH_SCHEMA) == ["query"]

def test_web_search_num_results_is_optional():
    assert "num_results" not in get_required(WEB_SEARCH_SCHEMA)

def test_web_search_num_results_type():
    prop = get_properties(WEB_SEARCH_SCHEMA)["num_results"]
    assert prop["type"] == "integer"

def test_web_search_description_covers_when_to_use():
    desc = WEB_SEARCH_SCHEMA["function"]["description"]
    assert "internet" in desc.lower()
    assert "do not" in desc.lower()

# Text intelligence schemas

@pytest.mark.parametrize("schema", [
    ANALYZE_TEXT_SCHEMA, CLASSIFY_TEXT_SCHEMA, SEND_CHAT_MESSAGE_SCHEMA,
    LIST_CONVERSATIONS_SCHEMA, GET_CHAT_HISTORY_SCHEMA,
])
def test_text_intelligence_schema_structure(schema):
    assert schema["type"] == "function"
    fn = schema["function"]
    assert "name" in fn and fn["name"]
    assert "description" in fn and fn["description"]
    assert get_params(schema)["type"] == "object"

def test_analyze_text_required_fields():
    assert get_required(ANALYZE_TEXT_SCHEMA) == ["text"]

def test_classify_text_required_fields():
    assert get_required(CLASSIFY_TEXT_SCHEMA) == ["text"]

def test_analyze_and_classify_descriptions_are_distinct():
    analyze_desc = ANALYZE_TEXT_SCHEMA["function"]["description"].lower()
    classify_desc = CLASSIFY_TEXT_SCHEMA["function"]["description"].lower()
    assert "do not" in analyze_desc
    assert "do not" in classify_desc

def test_send_chat_message_conversation_id_is_optional():
    assert get_required(SEND_CHAT_MESSAGE_SCHEMA) == ["message"]
    assert "conversation_id" in get_properties(SEND_CHAT_MESSAGE_SCHEMA)

def test_list_conversations_takes_no_arguments():
    assert get_required(LIST_CONVERSATIONS_SCHEMA) == []
    assert get_properties(LIST_CONVERSATIONS_SCHEMA) == {}

def test_get_chat_history_required_fields():
    assert get_required(GET_CHAT_HISTORY_SCHEMA) == ["conversation_id"]

# TOOL_CATEGORIES

def test_tool_categories_has_data_lookup():
    assert "data_lookup" in TOOL_CATEGORIES

def test_tool_categories_has_computation():
    assert "computation" in TOOL_CATEGORIES

def test_tool_categories_has_text_intelligence():
    assert "text_intelligence" in TOOL_CATEGORIES

def test_data_lookup_contains_weather_and_search():
    names = [s["function"]["name"] for s in TOOL_CATEGORIES["data_lookup"]]
    assert "get_weather" in names
    assert "web_search" in names

def test_computation_contains_calculator():
    names = [s["function"]["name"] for s in TOOL_CATEGORIES["computation"]]
    assert "calculator" in names

def test_text_intelligence_contains_all_five():
    names = {s["function"]["name"] for s in TOOL_CATEGORIES["text_intelligence"]}
    assert names == {
        "analyze_text", "classify_text", "send_chat_message",
        "list_conversations", "get_chat_history",
    }

# ALL_TOOLS flat list

def test_all_tools_contains_every_registered_tool():
    names = {s["function"]["name"] for s in ALL_TOOLS}
    assert names == {
        "get_weather", "calculator", "web_search",
        "analyze_text", "classify_text", "send_chat_message",
        "list_conversations", "get_chat_history",
    }

def test_all_tools_no_duplicates():
    names = [s["function"]["name"] for s in ALL_TOOLS]
    assert len(names) == len(set(names))
