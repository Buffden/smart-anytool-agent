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
            "a mathematical expression: arithmetic, percentages, exponents, etc. "
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
            "Do NOT use for math problems or weather; those have dedicated tools."
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

ANALYZE_TEXT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_text",
        "description": (
            "Use this tool when the user gives you a block of text and asks for a "
            "summary, sentiment, key topics, or general analysis of it. "
            "Do NOT use this to assign the text a single category label; use "
            "classify_text for that."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze. Must be non-empty and no more than 5000 characters.",
                },
            },
            "required": ["text"],
        },
    },
}

CLASSIFY_TEXT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "classify_text",
        "description": (
            "Use this tool when the user asks what category or topic a block of "
            "text belongs to (technology, politics, sports, business, health, or "
            "other). Do NOT use this for summarization or sentiment; use "
            "analyze_text for that."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to classify. Must be non-empty and no more than 5000 characters.",
                },
            },
            "required": ["text"],
        },
    },
}

SEND_CHAT_MESSAGE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_chat_message",
        "description": (
            "Use this tool to send a message to the backend's own chat assistant "
            "and get a reply, continuing an existing conversation if a "
            "conversation_id is already known from earlier in this session. "
            "Do NOT use this for weather, search, or math."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send. Must be non-empty.",
                },
                "conversation_id": {
                    "type": "string",
                    "description": (
                        "The ID of an existing conversation to continue. Omit this "
                        "to start a new conversation."
                    ),
                },
            },
            "required": ["message"],
        },
    },
}

LIST_CONVERSATIONS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_conversations",
        "description": (
            "Use this tool to list existing chat conversations, including their "
            "IDs, titles, and message counts. Useful when you need a "
            "conversation_id but don't already have one in context."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

GET_CHAT_HISTORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_chat_history",
        "description": (
            "Use this tool to retrieve the full message history of a specific "
            "chat conversation, given its conversation_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The ID of the conversation to retrieve history for.",
                },
            },
            "required": ["conversation_id"],
        },
    },
}

TOOL_CATEGORIES: dict[str, list[dict]] = {
    "data_lookup": [WEATHER_SCHEMA, WEB_SEARCH_SCHEMA],
    "computation": [CALCULATOR_SCHEMA],
    "text_intelligence": [
        ANALYZE_TEXT_SCHEMA,
        CLASSIFY_TEXT_SCHEMA,
        SEND_CHAT_MESSAGE_SCHEMA,
        LIST_CONVERSATIONS_SCHEMA,
        GET_CHAT_HISTORY_SCHEMA,
    ],
}

ALL_TOOLS: list[dict] = [
    schema
    for schemas in TOOL_CATEGORIES.values()
    for schema in schemas
]
