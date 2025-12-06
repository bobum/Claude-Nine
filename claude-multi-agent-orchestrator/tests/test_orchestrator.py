"""
Tests for orchestrator.py

Mocks CrewAI and git operations to test orchestration logic
without making LLM calls or modifying real repositories.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOrchestratorInit:
    """Test orchestrator initialization."""

    def test_load_config_from_file(self, temp_git_repo):
        """Test loading config from YAML file."""
        # Create a config file
        config_path = Path(temp_git_repo) / "config.yaml"
        config_path.write_text("""
main_branch: main
check_interval: 30
anthropic_api_key: test-key-123
""")

        # Create tasks file
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("""
features:
  - name: TestFeature
    branch: feature/test
    description: Test feature
""")

        # Create workspace
        (Path(temp_git_repo) / ".agent-workspace").mkdir()

        # Change to temp repo
        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                # Make API call fail so it falls back to file
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="config.yaml",
                    tasks_path="tasks.yaml"
                )

                assert orchestrator.config.get('main_branch') == 'main'
                assert len(orchestrator.tasks_config) == 1
        finally:
            os.chdir(old_cwd)

    def test_load_config_defaults_on_missing_file(self, temp_git_repo):
        """Test that defaults are used when config file is missing."""
        # Create workspace
        (Path(temp_git_repo) / ".agent-workspace").mkdir()

        # Create minimal tasks file
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                # Should have defaults
                assert orchestrator.config.get('main_branch') == 'main'
        finally:
            os.chdir(old_cwd)


class TestTaskLoading:
    """Test task loading and parsing."""

    def test_load_tasks_from_features_key(self, temp_git_repo):
        """Test loading tasks from 'features' key in YAML."""
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("""
features:
  - name: Feature1
    branch: feature/one
    description: First feature
  - name: Feature2
    branch: feature/two
    description: Second feature
""")

        # Create workspace
        (Path(temp_git_repo) / ".agent-workspace").mkdir()

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                assert len(orchestrator.tasks_config) == 2
                assert orchestrator.tasks_config[0]['name'] == 'Feature1'
                assert orchestrator.tasks_config[1]['name'] == 'Feature2'
        finally:
            os.chdir(old_cwd)

    def test_load_tasks_empty_list(self, temp_git_repo):
        """Test handling of empty task list."""
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        (Path(temp_git_repo) / ".agent-workspace").mkdir()

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                assert orchestrator.tasks_config == []
        finally:
            os.chdir(old_cwd)

    def test_load_tasks_missing_file_returns_empty(self, temp_git_repo):
        """Test that missing tasks file returns empty list (resilient)."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="nonexistent_tasks.yaml"
                )

                # Should be empty, not crash
                assert orchestrator.tasks_config == []
        finally:
            os.chdir(old_cwd)


class TestPostCompletionPhases:
    """Test post-completion phases (push, merge)."""

    def test_push_all_branches(self, temp_git_repo):
        """Test pushing all feature branches."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                # Mock git_ops.push_branch
                orchestrator.git_ops.push_branch = Mock()
                orchestrator.feature_branches = ["feature/one", "feature/two"]

                pushed = orchestrator.push_all_branches()

                assert len(pushed) == 2
                assert orchestrator.git_ops.push_branch.call_count == 2
        finally:
            os.chdir(old_cwd)

    def test_push_all_branches_handles_failure(self, temp_git_repo):
        """Test that push failures don't stop other pushes."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                # First push fails, second succeeds
                orchestrator.git_ops.push_branch = Mock(
                    side_effect=[Exception("Push failed"), None]
                )
                orchestrator.feature_branches = ["feature/fail", "feature/success"]

                pushed = orchestrator.push_all_branches()

                # Only one succeeded
                assert pushed == ["feature/success"]
        finally:
            os.chdir(old_cwd)

    def test_merge_all_branches_success(self, temp_git_repo):
        """Test successful merge of all branches."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                # Mock successful merge
                orchestrator.git_ops.merge_branches_into_integration = Mock(
                    return_value={
                        "success": True,
                        "integration_branch": "integration/test",
                        "merged_branches": ["feature/one", "feature/two"],
                        "failed_branch": None,
                        "conflicting_files": []
                    }
                )
                orchestrator.git_ops.push_branch = Mock()
                orchestrator.feature_branches = ["feature/one", "feature/two"]

                result = orchestrator.merge_all_branches()

                assert result["success"] is True
                assert result["integration_branch"] == "integration/test"
                orchestrator.git_ops.push_branch.assert_called_with("integration/test")
        finally:
            os.chdir(old_cwd)

    def test_merge_all_branches_with_conflict(self, temp_git_repo):
        """Test merge failure due to conflicts."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                # Mock failed merge
                orchestrator.git_ops.merge_branches_into_integration = Mock(
                    return_value={
                        "success": False,
                        "integration_branch": "integration/test",
                        "merged_branches": ["feature/one"],
                        "failed_branch": "feature/two",
                        "conflicting_files": ["conflict.txt"]
                    }
                )
                orchestrator.feature_branches = ["feature/one", "feature/two"]

                result = orchestrator.merge_all_branches()

                assert result["success"] is False
                assert result["failed_branch"] == "feature/two"
                assert "conflict.txt" in result["conflicting_files"]
        finally:
            os.chdir(old_cwd)

    def test_merge_all_branches_empty_list(self, temp_git_repo):
        """Test merge with no feature branches."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                orchestrator.feature_branches = []

                result = orchestrator.merge_all_branches()

                assert result["success"] is True
                assert result["integration_branch"] is None
        finally:
            os.chdir(old_cwd)


class TestAgentCreation:
    """Test agent and task creation (mocked)."""

    def test_create_feature_agent_tracks_branch(self, temp_git_repo):
        """Test that creating an agent tracks its branch."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                # Need to mock CrewAI components
                with patch('orchestrator.Agent'), \
                     patch('orchestrator.LLM'):

                    from orchestrator import MultiAgentOrchestrator

                    orchestrator = MultiAgentOrchestrator(
                        config_path="nonexistent.yaml",
                        tasks_path="tasks.yaml"
                    )

                    # Mock worktree creation
                    orchestrator.git_ops.create_worktree = Mock(
                        return_value="/fake/worktree/path"
                    )

                    feature_config = {
                        "name": "TestFeature",
                        "branch": "feature/test",
                        "role": "Developer",
                        "goal": "Implement test feature"
                    }

                    agent, path = orchestrator.create_feature_agent(feature_config)

                    # Branch should be tracked
                    assert "feature/test" in orchestrator.feature_branches
        finally:
            os.chdir(old_cwd)


class TestCleanup:
    """Test cleanup operations."""

    def test_cleanup_removes_worktrees(self, temp_git_repo):
        """Test that cleanup removes all worktrees."""
        (Path(temp_git_repo) / ".agent-workspace").mkdir()
        tasks_path = Path(temp_git_repo) / "tasks.yaml"
        tasks_path.write_text("features: []")

        old_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            with patch('orchestrator.requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.RequestException("API not available")

                from orchestrator import MultiAgentOrchestrator

                orchestrator = MultiAgentOrchestrator(
                    config_path="nonexistent.yaml",
                    tasks_path="tasks.yaml"
                )

                # Add some fake worktrees
                orchestrator.worktrees = ["/path/one", "/path/two"]
                orchestrator.git_ops.cleanup_all_worktrees = Mock()

                # Call cleanup
                with patch('orchestrator.shutdown_telemetry'):
                    orchestrator.cleanup()

                orchestrator.git_ops.cleanup_all_worktrees.assert_called_once()
        finally:
            os.chdir(old_cwd)
