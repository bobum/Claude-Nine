"""
Pytest fixtures for orchestrator tests.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from git import Repo


@pytest.fixture
def temp_git_repo():
    """
    Create a temporary git repository for testing.

    Yields the repo path and cleans up after the test.
    """
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="claude9_test_")

    # Initialize git repo
    repo = Repo.init(temp_dir)

    # Configure git user (required for commits)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Create initial commit on main
    readme_path = Path(temp_dir) / "README.md"
    readme_path.write_text("# Test Repository\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    # Rename default branch to main if needed
    if repo.active_branch.name != "main":
        repo.active_branch.rename("main")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_git_repo_with_remote():
    """
    Create a temporary git repository with a bare remote for testing push/pull.

    Yields a tuple of (local_repo_path, remote_repo_path).
    """
    # Create temp directories
    base_dir = tempfile.mkdtemp(prefix="claude9_test_")
    remote_dir = os.path.join(base_dir, "remote.git")
    local_dir = os.path.join(base_dir, "local")

    # Create bare remote repo
    Repo.init(remote_dir, bare=True)

    # Clone to local
    local_repo = Repo.clone_from(remote_dir, local_dir)

    # Configure git user
    local_repo.config_writer().set_value("user", "name", "Test User").release()
    local_repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Create initial commit on main
    readme_path = Path(local_dir) / "README.md"
    readme_path.write_text("# Test Repository\n")
    local_repo.index.add(["README.md"])
    local_repo.index.commit("Initial commit")

    # Push to remote
    local_repo.remote("origin").push("HEAD:main")

    # Set up tracking
    local_repo.heads.main.set_tracking_branch(local_repo.remotes.origin.refs.main)

    yield local_dir, remote_dir

    # Cleanup
    shutil.rmtree(base_dir, ignore_errors=True)


@pytest.fixture
def temp_workspace():
    """
    Create a temporary workspace directory for worktree tests.
    """
    temp_dir = tempfile.mkdtemp(prefix="claude9_workspace_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
