import httpx
from duckduckgo_search import DDGS

from config import settings


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
