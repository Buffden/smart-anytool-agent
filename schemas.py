WEATHER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Use this tool when the user asks about current weather conditions, "
            "temperature, humidity, wind, or forecast for a specific city or location. "
            "Do NOT use for historical climate data or general geography questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country in plain English, e.g. 'Tokyo, Japan'.",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit. Defaults to celsius if not specified.",
                },
            },
            "required": ["location"],
        },
    },
}

CALCULATOR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": (
            "Use this tool when the user asks to compute, calculate, or evaluate "
            "a mathematical expression — arithmetic, percentages, exponents, etc. "
            "Do NOT use for unit conversions or symbolic algebra."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": (
                        "A safe mathematical expression using numbers and operators "
                        "(+, -, *, /, **, %). Example: '(12 * 3) / 4 + 2 ** 3'."
                    ),
                },
            },
            "required": ["expression"],
        },
    },
}

WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Use this tool when the user asks for recent news, current events, "
            "facts that may have changed since the model's training cutoff, or "
            "any question that requires live information from the internet. "
            "Do NOT use for math problems or weather — those have dedicated tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A concise search query optimised for a web search engine.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return. Defaults to 5.",
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_CATEGORIES: dict[str, list[dict]] = {
    "data_lookup": [WEATHER_SCHEMA, WEB_SEARCH_SCHEMA],
    "computation": [CALCULATOR_SCHEMA],
}

ALL_TOOLS: list[dict] = [
    schema
    for schemas in TOOL_CATEGORIES.values()
    for schema in schemas
]
