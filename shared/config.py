"""
Unified Configuration Management for Claude-Nine

This module provides a single source of truth for all configuration settings
used by both the API and the Orchestrator. Uses Pydantic BaseSettings for
validation and automatic loading from environment variables and .env files.

Usage:
    from shared.config import settings

    # Access any setting
    api_key = settings.anthropic_api_key
    port = settings.api_port
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Optional[Path]:
    """
    Find the .env file by checking multiple locations.

    Search order:
    1. api/.env (primary location)
    2. .env in project root
    3. Current working directory
    """
    # Get the project root (where shared/ lives)
    project_root = Path(__file__).parent.parent

    # Check api/.env first (primary location)
    api_env = project_root / "api" / ".env"
    if api_env.exists():
        return api_env

    # Check project root
    root_env = project_root / ".env"
    if root_env.exists():
        return root_env

    # Check current working directory
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env

    # Also check api/.env relative to cwd (for orchestrator subprocess)
    cwd_api_env = Path.cwd() / "api" / ".env"
    if cwd_api_env.exists():
        return cwd_api_env

    return None


class Settings(BaseSettings):
    """
    Unified application settings for Claude-Nine.

    All settings are loaded from environment variables and/or .env files.
    Settings are validated on load - invalid values will raise errors early.

    Environment variables take precedence over .env file values.
    """

    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    database_url: str = "sqlite:///./claude_nine.db"

    # ==========================================================================
    # API Server Configuration
    # ==========================================================================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # ==========================================================================
    # Security
    # ==========================================================================
    secret_key: str = "change-me-in-production"

    # ==========================================================================
    # Anthropic API (Required for Claude AI)
    # ==========================================================================
    anthropic_api_key: str = ""

    # ==========================================================================
    # Orchestrator Configuration
    # ==========================================================================
    # Force dry-run mode (mock LLM, no API credits consumed)
    force_dry_run: bool = False

    # Default git branch for orchestrator operations
    main_branch: str = "main"

    # Interval in seconds for orchestrator health checks
    check_interval: int = 60

    # API URL for orchestrator to report back to (set by API when spawning)
    claude_nine_api_url: str = "http://localhost:8000"

    # ==========================================================================
    # Integration Credentials (Optional)
    # ==========================================================================
    # Azure DevOps
    azure_devops_url: str = ""
    azure_devops_organization: str = ""
    azure_devops_token: str = ""
    ado_pat: str = ""  # Alias for azure_devops_token

    # Jira
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    # GitHub
    github_token: str = ""

    # Linear
    linear_api_key: str = ""

    model_config = SettingsConfigDict(
        # Load from .env file (found dynamically)
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        # Environment variables are case-insensitive
        case_sensitive=False,
        # Don't fail if .env doesn't exist
        env_ignore_empty=True,
        # Allow extra fields (forward compatibility)
        extra="ignore",
    )

    @property
    def is_api_key_configured(self) -> bool:
        """Check if a valid Anthropic API key is configured."""
        return bool(self.anthropic_api_key and self.anthropic_api_key.startswith("sk-"))

    @property
    def effective_dry_run(self) -> bool:
        """
        Determine if dry-run mode should be used.

        Returns True if:
        - force_dry_run is True, OR
        - No valid API key is configured
        """
        if self.force_dry_run:
            return True
        if not self.is_api_key_configured:
            return True
        return False


@lru_cache()
def get_settings() -> Settings:
    """
    Get the cached settings instance.

    Uses lru_cache to ensure settings are only loaded once per process.
    """
    return Settings()


# Global settings instance for convenient access
# Usage: from shared.config import settings
settings = get_settings()
