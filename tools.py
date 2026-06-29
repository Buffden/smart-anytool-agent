import httpx
from duckduckgo_search import DDGS


def get_weather(location: str, unit: str = "celsius") -> dict:
    url = f"https://wttr.in/{location}?format=j1"

    try:
        response = httpx.get(url, timeout = 10)
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


def web_search(query: str, num_results: int = 5) -> list[dict]:
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
