import json
from typing import Literal
from pydantic import BaseModel, ValidationError, Field
import tools as _tools
from config import settings

# data contracts / validators

class GetWeatherArgs(BaseModel):
    location: str
    unit: Literal["celsius", "fahrenheit"] = settings.weather_default_unit


class WebSearchArgs(BaseModel):
    query: str
    num_results: int = Field(default=settings.web_search_default_results, gt=0)


class CalculatorArgs(BaseModel):
    expression: str


_REGISTRY: dict[str, tuple] = {
    "get_weather": (GetWeatherArgs, "get_weather"),
    "web_search":  (WebSearchArgs,  "web_search"),
    "calculator":  (CalculatorArgs, "calculator"),
}


def dispatch(tool_name: str, raw_args: str) -> dict:

    # Is the tool name known?
    if tool_name not in _REGISTRY:
        return {"error": f"Unknown tool: '{tool_name}'"}

    # Is the JSON valid?
    try:
        args_dict = json.loads(raw_args)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON arguments: {e}"}

    validator, fn_name = _REGISTRY[tool_name]

    # are the arguments valid?
    try:
        validated = validator(**args_dict)
    except ValidationError as e:
        return {"error": f"Argument validation failed: {e}"}

    # calling the actual function now
    fn = getattr(_tools, fn_name)
    return fn(**validated.model_dump())
