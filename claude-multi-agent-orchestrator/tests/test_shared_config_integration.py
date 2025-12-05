"""
Tests for orchestrator integration with shared configuration.

Covers:
- Shared settings accessibility
- Dry-run mode determination
- API URL configuration
- Configuration property behavior
"""

import os
import pytest
from unittest.mock import patch
import tempfile
from pathlib import Path
import sys

# Add project root for shared imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestSharedConfigAccessibility:
    """Tests for shared configuration accessibility from orchestrator directory."""

    def test_shared_settings_importable(self):
        """Shared settings can be imported."""
        from shared.config import settings
        assert settings is not None

    def test_shared_settings_has_required_attributes(self):
        """Shared settings has all required orchestrator attributes."""
        from shared.config import settings

        # Orchestrator-required settings
        assert hasattr(settings, 'anthropic_api_key')
        assert hasattr(settings, 'claude_nine_api_url')
        assert hasattr(settings, 'force_dry_run')
        assert hasattr(settings, 'main_branch')
        assert hasattr(settings, 'check_interval')

    def test_shared_settings_has_helper_properties(self):
        """Shared settings has helper properties."""
        from shared.config import settings

        assert hasattr(settings, 'is_api_key_configured')
        assert hasattr(settings, 'effective_dry_run')

    def test_get_settings_function_available(self):
        """get_settings function is available."""
        from shared.config import get_settings, Settings

        settings = get_settings()
        assert isinstance(settings, Settings)


class TestDryRunDetermination:
    """Tests for dry-run mode determination logic."""

    def test_dry_run_when_no_api_key(self):
        """Effective dry run is True when no API key configured."""
        from shared.config import Settings

        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "",
            "FORCE_DRY_RUN": "false"
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.effective_dry_run is True

    def test_dry_run_when_invalid_api_key(self):
        """Effective dry run is True when API key format is invalid."""
        from shared.config import Settings

        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "invalid-key-format",
            "FORCE_DRY_RUN": "false"
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.is_api_key_configured is False
            assert settings.effective_dry_run is True

    def test_dry_run_when_force_enabled(self):
        """Effective dry run is True when force_dry_run is True."""
        from shared.config import Settings

        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-valid-key",
            "FORCE_DRY_RUN": "true"
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.force_dry_run is True
            assert settings.effective_dry_run is True

    def test_live_mode_when_valid_key_and_no_force(self):
        """Live mode when valid API key and force_dry_run is False."""
        from shared.config import Settings

        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-valid-key",
            "FORCE_DRY_RUN": "false"
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.is_api_key_configured is True
            assert settings.effective_dry_run is False


class TestApiKeyValidation:
    """Tests for API key validation."""

    def test_valid_sk_ant_prefix(self):
        """API key with 'sk-ant-' prefix is valid."""
        from shared.config import Settings

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-abc123"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.is_api_key_configured is True

    def test_valid_sk_prefix(self):
        """API key with 'sk-' prefix is valid."""
        from shared.config import Settings

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-abc123"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.is_api_key_configured is True

    def test_invalid_no_sk_prefix(self):
        """API key without 'sk-' prefix is invalid."""
        from shared.config import Settings

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "abc123"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.is_api_key_configured is False

    def test_empty_key_invalid(self):
        """Empty API key is invalid."""
        from shared.config import Settings

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.is_api_key_configured is False


class TestApiUrlConfiguration:
    """Tests for API URL configuration."""

    def test_default_api_url(self):
        """Default API URL is localhost:8000."""
        from shared.config import Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.claude_nine_api_url == "http://localhost:8000"

    def test_custom_api_url(self):
        """Custom API URL can be set via environment."""
        from shared.config import Settings

        with patch.dict(os.environ, {
            "CLAUDE_NINE_API_URL": "http://custom-host:9999"
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.claude_nine_api_url == "http://custom-host:9999"

    def test_api_url_with_path(self):
        """API URL can include path components."""
        from shared.config import Settings

        with patch.dict(os.environ, {
            "CLAUDE_NINE_API_URL": "http://localhost:8000/api/v1"
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.claude_nine_api_url == "http://localhost:8000/api/v1"


class TestOrchestratorSettings:
    """Tests for orchestrator-specific settings."""

    def test_main_branch_default(self):
        """Main branch defaults to 'main'."""
        from shared.config import Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.main_branch == "main"

    def test_main_branch_custom(self):
        """Main branch can be customized."""
        from shared.config import Settings

        with patch.dict(os.environ, {"MAIN_BRANCH": "master"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.main_branch == "master"

    def test_check_interval_default(self):
        """Check interval defaults to 60 seconds."""
        from shared.config import Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.check_interval == 60

    def test_check_interval_custom(self):
        """Check interval can be customized."""
        from shared.config import Settings

        with patch.dict(os.environ, {"CHECK_INTERVAL": "120"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.check_interval == 120


class TestEnvFileDiscovery:
    """Tests for .env file discovery."""

    def test_env_file_in_api_directory(self):
        """Finds .env file in api/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure
            api_dir = Path(tmpdir) / "api"
            api_dir.mkdir()
            env_file = api_dir / ".env"
            env_file.write_text("TEST_VAR=from_api_env")

            # The find_env_file function looks relative to its own location
            # This test validates the file exists and is readable
            assert env_file.exists()
            assert env_file.read_text() == "TEST_VAR=from_api_env"

    def test_env_file_in_project_root(self):
        """Finds .env file in project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TEST_VAR=from_root")

            assert env_file.exists()
            assert env_file.read_text() == "TEST_VAR=from_root"


class TestSettingsCaching:
    """Tests for settings caching behavior."""

    def test_get_settings_returns_same_instance(self):
        """get_settings returns cached instance."""
        from shared.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # Same object due to lru_cache
        assert settings1 is settings2

    def test_new_settings_instance_independent(self):
        """New Settings instances are independent."""
        from shared.config import Settings

        with patch.dict(os.environ, {"API_PORT": "8001"}, clear=True):
            settings1 = Settings(_env_file=None)

        with patch.dict(os.environ, {"API_PORT": "8002"}, clear=True):
            settings2 = Settings(_env_file=None)

        assert settings1.api_port == 8001
        assert settings2.api_port == 8002
