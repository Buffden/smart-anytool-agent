from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""

    # Weather tool
    weather_api_url: str = "https://wttr.in/{location}?format=j1"
    http_timeout: int = 10
    weather_default_unit: str = "celsius"

    # Web search tool
    web_search_default_results: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
