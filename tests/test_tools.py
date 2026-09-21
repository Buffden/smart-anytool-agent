import datetime
import decimal

import httpx
import psycopg
import pytest
from unittest.mock import MagicMock, patch

from tools import (
    analyze_text,
    classify_text,
    get_chat_history,
    get_weather,
    list_conversations,
    query_database,
    send_chat_message,
    web_search,
)

# Fixtures

WTTR_RESPONSE = {
    "current_condition": [
        {
            "temp_C": "22",
            "temp_F": "72",
            "FeelsLikeC": "21",
            "FeelsLikeF": "70",
            "humidity": "60",
            "windspeedKmph": "15",
            "weatherDesc": [{"value": "Partly cloudy"}],
        }
    ]
}


def make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


# get_weather : success

def test_get_weather_returns_structured_data():
    with patch("tools.httpx.get", return_value=make_mock_response(WTTR_RESPONSE)):
        result = get_weather("London")

    assert result["location"] == "London"
    assert result["temperature"] == 22
    assert result["unit"] == "celsius"
    assert result["feels_like"] == 21
    assert result["humidity"] == 60
    assert result["description"] == "Partly cloudy"
    assert result["wind_speed_kmph"] == 15


def test_get_weather_fahrenheit():
    with patch("tools.httpx.get", return_value=make_mock_response(WTTR_RESPONSE)):
        result = get_weather("London", unit="fahrenheit")

    assert result["temperature"] == 72
    assert result["feels_like"] == 70
    assert result["unit"] == "fahrenheit"


def test_get_weather_temperature_is_int():
    with patch("tools.httpx.get", return_value=make_mock_response(WTTR_RESPONSE)):
        result = get_weather("London")

    assert isinstance(result["temperature"], int)
    assert isinstance(result["humidity"], int)
    assert isinstance(result["wind_speed_kmph"], int)


# get_weather : failure cases

def test_get_weather_city_not_found():
    mock = make_mock_response({}, status_code=404)
    mock.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=mock
    )
    with patch("tools.httpx.get", return_value=mock):
        result = get_weather("NotARealCity123")

    assert "error" in result


def test_get_weather_malformed_response():
    with patch("tools.httpx.get", return_value=make_mock_response({"unexpected": "data"})):
        result = get_weather("London")

    assert "error" in result


def test_get_weather_network_error():
    with patch("tools.httpx.get", side_effect=httpx.RequestError("timeout")):
        result = get_weather("London")

    assert "error" in result
    assert "weather service" in result["error"]


def test_get_weather_does_not_raise():
    with patch("tools.httpx.get", side_effect=Exception("unexpected")):
        result = get_weather("London")

    assert "error" in result


# web_search : success

DDGS_RESULTS = [
    {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
    {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
]


def test_web_search_returns_list_of_dicts():
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = DDGS_RESULTS

    with patch("tools.DDGS", return_value=mock_ddgs):
        results = web_search("python tutorials")

    assert isinstance(results, list)
    assert len(results) == 2


def test_web_search_result_has_title_url_snippet():
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = DDGS_RESULTS

    with patch("tools.DDGS", return_value=mock_ddgs):
        results = web_search("python tutorials")

    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r


def test_web_search_respects_num_results():
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = DDGS_RESULTS

    with patch("tools.DDGS", return_value=mock_ddgs):
        web_search("query", num_results=3)

    mock_ddgs.text.assert_called_once_with("query", max_results=3)


# web_search : failure cases

def test_web_search_empty_results():
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = []

    with patch("tools.DDGS", return_value=mock_ddgs):
        results = web_search("obscure query with no results")

    assert results == []


def test_web_search_failure_returns_error():
    with patch("tools.DDGS", side_effect=Exception("network error")):
        results = web_search("query")

    assert len(results) == 1
    assert "error" in results[0]


def test_web_search_does_not_raise():
    with patch("tools.DDGS", side_effect=Exception("unexpected")):
        results = web_search("query")

    assert isinstance(results, list)


# backend-connected tools : success

def test_analyze_text_returns_backend_response():
    body = {"summary": "...", "sentiment": "neutral", "confidence": 0.9,
             "key_topics": ["a"], "word_count_estimate": 42}
    with patch("tools.httpx.request", return_value=make_mock_response(body)):
        result = analyze_text("some text")

    assert result == body


def test_classify_text_returns_backend_response():
    body = {"category": "technology", "confidence": 0.8, "reasoning": "..."}
    with patch("tools.httpx.request", return_value=make_mock_response(body)):
        result = classify_text("some text")

    assert result == body


def test_send_chat_message_sends_conversation_id_in_payload():
    body = {"conversationId": "abc-123", "reply": "..."}
    with patch("tools.httpx.request", return_value=make_mock_response(body)) as mock:
        result = send_chat_message("hi", conversation_id="abc-123")

    assert result == body
    _, kwargs = mock.call_args
    assert kwargs["json"] == {"conversationId": "abc-123", "message": "hi"}


def test_send_chat_message_starts_new_conversation_when_id_omitted():
    body = {"conversationId": "new-id", "reply": "..."}
    with patch("tools.httpx.request", return_value=make_mock_response(body)) as mock:
        send_chat_message("hi")

    _, kwargs = mock.call_args
    assert kwargs["json"]["conversationId"] is None


def test_list_conversations_returns_list():
    body = [{"id": "abc-123", "title": "t", "createdAt": "...", "messageCount": 2}]
    with patch("tools.httpx.request", return_value=make_mock_response(body)):
        result = list_conversations()

    assert result == body


# backend-connected tools : failure cases

def test_backend_connect_error_returns_transport_kind():
    with patch("tools.httpx.request", side_effect=httpx.ConnectError("refused")):
        result = analyze_text("some text")

    assert result["kind"] == "transport"


def test_backend_timeout_returns_transport_kind():
    with patch("tools.httpx.request", side_effect=httpx.TimeoutException("slow")):
        result = analyze_text("some text")

    assert result["kind"] == "transport"


def test_backend_400_returns_validation_kind():
    mock = make_mock_response({"error": "text must not be blank"}, status_code=400)
    with patch("tools.httpx.request", return_value=mock):
        result = analyze_text("")

    assert result["kind"] == "validation"


def test_backend_404_returns_not_found_kind():
    # _call_backend's generic 404 classification. Verified live against the
    # real backend that /api/chat/{id}/history does NOT actually 404 for an
    # unknown id -- it returns 200 with an empty list (see the test below).
    # This test just confirms the classification logic works if some other
    # endpoint ever does return a 404.
    mock = make_mock_response({}, status_code=404)
    with patch("tools.httpx.request", return_value=mock):
        result = get_chat_history("nonexistent-id")

    assert result["kind"] == "not_found"


def test_get_chat_history_unknown_id_returns_empty_list_not_error():
    # Verified live: the backend returns 200 [] for an unknown conversationId
    # rather than a 404. "No history yet" and "bad id" are indistinguishable
    # from this response alone.
    with patch("tools.httpx.request", return_value=make_mock_response([])):
        result = get_chat_history("nonexistent-id")

    assert result == []


def test_backend_500_returns_server_kind():
    mock = make_mock_response({}, status_code=500)
    with patch("tools.httpx.request", return_value=mock):
        result = analyze_text("some text")

    assert result["kind"] == "server"


# query_database

def make_mock_db_connection(rows: list[dict]):
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = rows

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor

    return conn


def test_query_database_blocked_by_validator_never_calls_db():
    with patch("tools.psycopg.connect") as mock_connect:
        result = query_database("DELETE FROM employees WHERE id = 1")

    assert result["kind"] == "blocked"
    mock_connect.assert_not_called()


def test_query_database_returns_rows_on_success():
    conn = make_mock_db_connection([{"name": "Engineering"}])
    with patch("tools.psycopg.connect", return_value=conn):
        result = query_database("SELECT name FROM departments")

    assert result["kind"] == "ok"
    assert result["rows"] == [{"name": "Engineering"}]


def test_query_database_empty_result_has_empty_kind():
    conn = make_mock_db_connection([])
    with patch("tools.psycopg.connect", return_value=conn):
        result = query_database("SELECT name FROM departments WHERE name = 'Nobody'")

    assert result == {"rows": [], "kind": "empty"}


def test_query_database_serializes_decimal_and_date():
    conn = make_mock_db_connection([
        {"salary": decimal.Decimal("165000.00"), "hire_date": datetime.date(2021, 3, 1)}
    ])
    with patch("tools.psycopg.connect", return_value=conn):
        result = query_database("SELECT salary, hire_date FROM employees")

    assert result["rows"][0]["salary"] == 165000.0
    assert isinstance(result["rows"][0]["salary"], float)
    assert result["rows"][0]["hire_date"] == "2021-03-01"


def test_query_database_permission_denied_returns_permission_kind():
    with patch("tools.psycopg.connect", side_effect=psycopg.errors.InsufficientPrivilege("denied")):
        result = query_database("SELECT * FROM employees")

    assert result["kind"] == "permission"


def test_query_database_timeout_returns_timeout_kind():
    with patch("tools.psycopg.connect", side_effect=psycopg.errors.QueryCanceled("cancelled")):
        result = query_database("SELECT * FROM employees")

    assert result["kind"] == "timeout"


def test_query_database_connection_refused_returns_transport_kind():
    with patch("tools.psycopg.connect", side_effect=psycopg.OperationalError("refused")):
        result = query_database("SELECT * FROM employees")

    assert result["kind"] == "transport"


def test_query_database_undefined_column_returns_syntax_kind():
    with patch("tools.psycopg.connect", side_effect=psycopg.errors.UndefinedColumn("no such column")):
        result = query_database("SELECT favorite_color FROM employees")

    assert result["kind"] == "syntax"
