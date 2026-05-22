from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Vector DB
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "interview_questions"

    # Relational DB
    database_url: str = (
        "postgresql+asyncpg://jobcopilot:jobcopilot@localhost:5432/jobcopilot"
    )

    # Monitoring
    langsmith_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "job-copilot"

    # Auth
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Rate Limiting
    daily_call_limit: int = 20
    redis_url: str = "redis://localhost:6379"

    model_config = {
        "env_file": ("../.env", ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
