import pytest
from schemas import (
    ALL_TOOLS,
    CALCULATOR_SCHEMA,
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

# TOOL_CATEGORIES

def test_tool_categories_has_data_lookup():
    assert "data_lookup" in TOOL_CATEGORIES

def test_tool_categories_has_computation():
    assert "computation" in TOOL_CATEGORIES

def test_data_lookup_contains_weather_and_search():
    names = [s["function"]["name"] for s in TOOL_CATEGORIES["data_lookup"]]
    assert "get_weather" in names
    assert "web_search" in names

def test_computation_contains_calculator():
    names = [s["function"]["name"] for s in TOOL_CATEGORIES["computation"]]
    assert "calculator" in names

# ALL_TOOLS flat list

def test_all_tools_contains_all_three():
    names = {s["function"]["name"] for s in ALL_TOOLS}
    assert names == {"get_weather", "calculator", "web_search"}

def test_all_tools_no_duplicates():
    names = [s["function"]["name"] for s in ALL_TOOLS]
    assert len(names) == len(set(names))
