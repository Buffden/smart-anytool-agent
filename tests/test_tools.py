import httpx
import pytest
from unittest.mock import MagicMock, patch

from tools import get_weather, web_search

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


# get_weather — success

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


# get_weather — failure cases

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


# web_search — success

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


# web_search — failure cases

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
