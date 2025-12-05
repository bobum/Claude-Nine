from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Orchestrator - force dry-run mode (no Anthropic API calls)
    force_dry_run: bool = False

    # Security
    secret_key: str

    # External APIs
    anthropic_api_key: str = ""
    ado_pat: str = ""

    # Celery / Redis task queue
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
