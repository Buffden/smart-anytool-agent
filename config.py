from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.0
    
    # Weather tool
    weather_api_url: str = "https://wttr.in/{location}?format=j1"
    http_timeout: int = 10
    weather_default_unit: str = "celsius"

    # Web search tool
    web_search_default_results: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
