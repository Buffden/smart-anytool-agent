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

    # Backend API tools
    backend_base_url: str = "http://localhost:8080"
    backend_http_timeout: int = 10

    # Database tools
    agent_db_dsn: str = "postgresql://agent_readonly:change_me@localhost:5433/ops_db"
    db_statement_timeout_ms: int = 5000

    # Agent loop
    agent_max_iterations: int = 5

    # Self-reflection
    retriever_max_retries: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
