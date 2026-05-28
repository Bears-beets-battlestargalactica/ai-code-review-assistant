from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Code Review Assistant"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    openrouter_api_key: str | None = None
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    github_token: str | None = None
    database_url: str = "sqlite:///./review_assistant.db"
    redis_url: str = "redis://localhost:6379/0"
    max_file_chars: int = 18000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
