import httpx
import ast
import datetime
import decimal
from duckduckgo_search import DDGS
import psycopg
from psycopg.rows import dict_row

from config import settings
from db_validation import validate_select


def get_weather(location: str, unit: str = settings.weather_default_unit) -> dict:
    url = settings.weather_api_url.format(location=location)

    try:
        response = httpx.get(url, timeout=settings.http_timeout)
        response.raise_for_status()
        data = response.json()

        current = data["current_condition"][0]
        temp_key = "temp_C" if unit == "celsius" else "temp_F"
        feels_key = "FeelsLikeC" if unit == "celsius" else "FeelsLikeF"

        return {
            "location": location,
            "temperature": int(current[temp_key]),
            "unit": unit,
            "feels_like": int(current[feels_key]),
            "humidity": int(current["humidity"]),
            "description": current["weatherDesc"][0]["value"],
            "wind_speed_kmph": int(current["windspeedKmph"]),
        }

    except httpx.HTTPStatusError:
        return {"error": f"Location '{location}' not found."}
    except (KeyError, IndexError, ValueError):
        return {"error": f"Unexpected response format for '{location}'."}
    except httpx.RequestError as e:
        return {"error": f"Could not reach weather service: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def web_search(query: str, num_results: int = settings.web_search_default_results) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))

        return [
            {
                "title": r["title"],
                "url": r["href"],
                "snippet": r["body"],
            }
            for r in results
        ]

    except Exception as e:
        return [{"error": f"Search failed: {e}"}]

ALLOWED_NODES = {                                                                                         
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.USub,
    ast.Constant,
}

def calculator(expression: str) -> dict:
    try:
        tree = ast.parse(expression, mode="eval")

        for node in ast.walk(tree):
            if type(node) not in ALLOWED_NODES:
                return {"error": f"Unsafe expression: {type(node).__name__} is not allowed"}
            if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
                return {"error": f"Unsafe expression: only numeric constants are allowed"}

        result = eval(compile(tree, filename="", mode="eval"))
        return { "expression": expression, "result": result }

    except ZeroDivisionError:
        return {"error": "Division by zero"}
    except SyntaxError:
        return {"error": "Invalid expression"}


def _call_backend(method: str, path: str, **kwargs) -> dict:
    try:
        response = httpx.request(
            method,
            f"{settings.backend_base_url}{path}",
            timeout=settings.backend_http_timeout,
            **kwargs,
        )
    except httpx.ConnectError:
        return {"error": "Backend is unreachable. Is it running?", "kind": "transport"}
    except httpx.TimeoutException:
        return {"error": "Backend did not respond in time.", "kind": "transport"}

    if response.status_code == 400:
        return {"error": response.json(), "kind": "validation"}
    if response.status_code == 404:
        return {"error": "Not found.", "kind": "not_found"}
    if response.status_code >= 500:
        return {"error": f"Backend error ({response.status_code}).", "kind": "server"}

    return response.json()


def analyze_text(text: str) -> dict:
    return _call_backend("POST", "/api/analyze", json={"text": text})


def classify_text(text: str) -> dict:
    return _call_backend("POST", "/api/classify", json={"text": text})


def send_chat_message(message: str, conversation_id: str | None = None) -> dict:
    return _call_backend(
        "POST",
        "/api/chat",
        json={"conversationId": conversation_id, "message": message},
    )


def get_chat_history(conversation_id: str) -> list | dict:
    return _call_backend("GET", f"/api/chat/{conversation_id}/history")


def list_conversations() -> list | dict:
    return _call_backend("GET", "/api/chat/conversations")


def _json_safe(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def query_database(sql: str) -> dict:
    try:
        safe_sql = validate_select(sql)
    except ValueError as e:
        return {"error": str(e), "kind": "blocked"}

    try:
        with psycopg.connect(
            settings.agent_db_dsn,
            autocommit=True,
            options=f"-c statement_timeout={settings.db_statement_timeout_ms}",
        ) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(safe_sql)
                rows = cur.fetchall()
    except psycopg.errors.InsufficientPrivilege:
        return {"error": "This query was rejected by the database's read-only role.", "kind": "permission"}
    except psycopg.errors.QueryCanceled:
        return {"error": "The query took too long and was cancelled.", "kind": "timeout"}
    except psycopg.OperationalError as e:
        return {"error": f"Could not reach the database: {e}", "kind": "transport"}
    except psycopg.Error as e:
        return {"error": str(e), "kind": "syntax"}

    rows = [{k: _json_safe(v) for k, v in row.items()} for row in rows]

    if not rows:
        return {"rows": [], "kind": "empty"}
    return {"rows": rows, "kind": "ok"}