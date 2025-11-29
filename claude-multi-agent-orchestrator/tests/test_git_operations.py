"""
Tests for git_operations.py

Uses temporary git repositories to test git operations in isolation.
"""

import os
import pytest
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from git_operations import GitOperations
from git import Repo


class TestGitOperationsBasic:
    """Test basic git operations."""

    def test_init_with_valid_repo(self, temp_git_repo):
        """Test initializing GitOperations with a valid repo."""
        git_ops = GitOperations(temp_git_repo)
        assert git_ops.repo_path == temp_git_repo

    def test_init_with_invalid_repo(self, temp_workspace):
        """Test initializing GitOperations with an invalid path."""
        with pytest.raises(ValueError, match="not a valid git repository"):
            GitOperations(temp_workspace)

    def test_get_current_branch(self, temp_git_repo):
        """Test getting the current branch name."""
        git_ops = GitOperations(temp_git_repo)
        assert git_ops.get_current_branch() == "main"

    def test_branch_exists(self, temp_git_repo):
        """Test checking if a branch exists."""
        git_ops = GitOperations(temp_git_repo)
        assert git_ops.branch_exists("main") is True
        assert git_ops.branch_exists("nonexistent") is False

    def test_get_all_branches(self, temp_git_repo):
        """Test getting all branch names."""
        git_ops = GitOperations(temp_git_repo)
        branches = git_ops.get_all_branches()
        assert "main" in branches


class TestBranchOperations:
    """Test branch creation and management."""

    def test_create_branch_from_main(self, temp_git_repo):
        """Test creating a new branch from main."""
        git_ops = GitOperations(temp_git_repo)
        git_ops.create_branch_from_main("feature/test")

        assert git_ops.branch_exists("feature/test")
        assert git_ops.get_current_branch() == "feature/test"

    def test_create_existing_branch_checks_out(self, temp_git_repo):
        """Test that creating an existing branch just checks it out."""
        git_ops = GitOperations(temp_git_repo)

        # Create branch first
        git_ops.create_branch_from_main("feature/existing")
        git_ops.repo.heads.main.checkout()

        # Try to create again - should just checkout
        git_ops.create_branch_from_main("feature/existing")
        assert git_ops.get_current_branch() == "feature/existing"

    def test_delete_branch(self, temp_git_repo):
        """Test deleting a branch."""
        git_ops = GitOperations(temp_git_repo)

        # Create and checkout branch
        git_ops.create_branch_from_main("feature/to-delete")
        git_ops.repo.heads.main.checkout()

        # Delete it
        git_ops.delete_branch("feature/to-delete")
        assert not git_ops.branch_exists("feature/to-delete")

    def test_delete_nonexistent_branch(self, temp_git_repo):
        """Test deleting a branch that doesn't exist (should not error)."""
        git_ops = GitOperations(temp_git_repo)
        git_ops.delete_branch("nonexistent")  # Should not raise


class TestCommitOperations:
    """Test commit operations."""

    def test_commit_changes(self, temp_git_repo):
        """Test committing changes."""
        git_ops = GitOperations(temp_git_repo)

        # Create a new file
        test_file = Path(temp_git_repo) / "test.txt"
        test_file.write_text("test content")

        # Commit
        result = git_ops.commit_changes("Add test file")
        assert result is True

        # Verify commit
        commits = list(git_ops.repo.iter_commits("main", max_count=1))
        assert "Add test file" in commits[0].message

    def test_commit_no_changes(self, temp_git_repo):
        """Test committing when there are no changes."""
        git_ops = GitOperations(temp_git_repo)
        result = git_ops.commit_changes("No changes")
        assert result is False

    def test_get_recent_commits(self, temp_git_repo):
        """Test getting recent commits."""
        git_ops = GitOperations(temp_git_repo)

        # Add a few commits
        for i in range(3):
            test_file = Path(temp_git_repo) / f"file{i}.txt"
            test_file.write_text(f"content {i}")
            git_ops.commit_changes(f"Add file {i}")

        commits = git_ops.get_recent_commits("main", count=3)
        assert len(commits) == 3
        assert "Add file 2" in commits[0]

    def test_get_branch_commits_ahead_of_main(self, temp_git_repo):
        """Test counting commits ahead of main."""
        git_ops = GitOperations(temp_git_repo)

        # Create feature branch
        git_ops.create_branch_from_main("feature/ahead")

        # Add commits to feature branch
        for i in range(2):
            test_file = Path(temp_git_repo) / f"feature{i}.txt"
            test_file.write_text(f"feature {i}")
            git_ops.commit_changes(f"Feature commit {i}")

        ahead = git_ops.get_branch_commits_ahead_of_main("feature/ahead")
        assert ahead == 2


class TestWorktreeOperations:
    """Test worktree operations."""

    def test_create_worktree(self, temp_git_repo, temp_workspace):
        """Test creating a worktree."""
        git_ops = GitOperations(temp_git_repo)

        worktree_path = os.path.join(temp_workspace, "worktree-test")
        result = git_ops.create_worktree("feature/worktree", worktree_path)

        assert os.path.exists(result)
        assert git_ops.branch_exists("feature/worktree")

        # Verify worktree has its own checkout
        worktree_repo = Repo(result)
        assert worktree_repo.active_branch.name == "feature/worktree"

    def test_list_worktrees(self, temp_git_repo, temp_workspace):
        """Test listing worktrees."""
        git_ops = GitOperations(temp_git_repo)

        # Create a worktree
        worktree_path = os.path.join(temp_workspace, "worktree-list")
        git_ops.create_worktree("feature/list", worktree_path)

        worktrees = git_ops.list_worktrees()
        assert len(worktrees) >= 2  # Main repo + worktree

        # Find our worktree
        wt_paths = [wt["path"] for wt in worktrees]
        assert any("worktree-list" in p for p in wt_paths)

    def test_remove_worktree(self, temp_git_repo, temp_workspace):
        """Test removing a worktree."""
        git_ops = GitOperations(temp_git_repo)

        worktree_path = os.path.join(temp_workspace, "worktree-remove")
        git_ops.create_worktree("feature/remove", worktree_path)
        assert os.path.exists(worktree_path)

        git_ops.remove_worktree(worktree_path)
        assert not os.path.exists(worktree_path)

    def test_cleanup_all_worktrees(self, temp_git_repo, temp_workspace):
        """Test cleaning up all worktrees in a workspace."""
        git_ops = GitOperations(temp_git_repo)

        # Create multiple worktrees
        for i in range(3):
            worktree_path = os.path.join(temp_workspace, f"worktree-{i}")
            git_ops.create_worktree(f"feature/cleanup-{i}", worktree_path)

        git_ops.cleanup_all_worktrees(temp_workspace)

        # All worktrees should be gone
        worktrees = git_ops.list_worktrees()
        for wt in worktrees:
            assert temp_workspace not in wt["path"]


class TestMergeOperations:
    """Test merge operations."""

    def test_merge_branch_success(self, temp_git_repo):
        """Test successful branch merge."""
        git_ops = GitOperations(temp_git_repo)

        # Create feature branch with changes
        git_ops.create_branch_from_main("feature/merge-test")
        test_file = Path(temp_git_repo) / "feature.txt"
        test_file.write_text("feature content")
        git_ops.commit_changes("Add feature")

        # Merge into main
        result = git_ops.merge_branch("feature/merge-test", "main")
        assert result is True

        # Verify file exists on main
        git_ops.repo.heads.main.checkout()
        assert test_file.exists()

    def test_merge_branches_into_integration_success(self, temp_git_repo):
        """Test merging multiple branches into integration branch."""
        git_ops = GitOperations(temp_git_repo)

        # Create two feature branches with non-conflicting changes
        git_ops.create_branch_from_main("feature/one")
        (Path(temp_git_repo) / "one.txt").write_text("one")
        git_ops.commit_changes("Add one")

        git_ops.repo.heads.main.checkout()
        git_ops.create_branch_from_main("feature/two")
        (Path(temp_git_repo) / "two.txt").write_text("two")
        git_ops.commit_changes("Add two")

        # Merge both into integration
        result = git_ops.merge_branches_into_integration(
            feature_branches=["feature/one", "feature/two"],
            main_branch="main"
        )

        assert result["success"] is True
        assert "feature/one" in result["merged_branches"]
        assert "feature/two" in result["merged_branches"]
        assert result["integration_branch"].startswith("integration/")
        assert result["failed_branch"] is None

    def test_merge_branches_into_integration_with_conflict(self, temp_git_repo):
        """Test merge failure due to conflicts."""
        git_ops = GitOperations(temp_git_repo)

        # Create first branch modifying a file
        git_ops.create_branch_from_main("feature/conflict-a")
        conflict_file = Path(temp_git_repo) / "conflict.txt"
        conflict_file.write_text("version A")
        git_ops.commit_changes("Version A")

        # Create second branch with conflicting changes
        git_ops.repo.heads.main.checkout()
        git_ops.create_branch_from_main("feature/conflict-b")
        conflict_file.write_text("version B")
        git_ops.commit_changes("Version B")

        # Try to merge both - should fail on second
        result = git_ops.merge_branches_into_integration(
            feature_branches=["feature/conflict-a", "feature/conflict-b"],
            main_branch="main"
        )

        assert result["success"] is False
        assert "feature/conflict-a" in result["merged_branches"]
        assert result["failed_branch"] == "feature/conflict-b"

    def test_merge_branches_into_integration_custom_branch_name(self, temp_git_repo):
        """Test merge with custom integration branch name."""
        git_ops = GitOperations(temp_git_repo)

        # Create a feature branch
        git_ops.create_branch_from_main("feature/custom")
        (Path(temp_git_repo) / "custom.txt").write_text("custom")
        git_ops.commit_changes("Add custom")

        # Merge with custom branch name
        result = git_ops.merge_branches_into_integration(
            feature_branches=["feature/custom"],
            integration_branch="release/v1.0"
        )

        assert result["success"] is True
        assert result["integration_branch"] == "release/v1.0"

    def test_merge_branches_skips_nonexistent(self, temp_git_repo):
        """Test that nonexistent branches are skipped."""
        git_ops = GitOperations(temp_git_repo)

        # Create one real branch
        git_ops.create_branch_from_main("feature/real")
        (Path(temp_git_repo) / "real.txt").write_text("real")
        git_ops.commit_changes("Add real")

        # Try to merge with a nonexistent branch
        result = git_ops.merge_branches_into_integration(
            feature_branches=["feature/real", "feature/nonexistent"]
        )

        assert result["success"] is True
        assert "feature/real" in result["merged_branches"]
        assert "feature/nonexistent" not in result["merged_branches"]


class TestFileOperations:
    """Test file read/write operations."""

    def test_get_file_content_from_working_dir(self, temp_git_repo):
        """Test reading file from working directory."""
        git_ops = GitOperations(temp_git_repo)

        content = git_ops.get_file_content("README.md")
        assert "# Test Repository" in content

    def test_get_file_content_from_branch(self, temp_git_repo):
        """Test reading file from a specific branch."""
        git_ops = GitOperations(temp_git_repo)

        # Create branch with new file
        git_ops.create_branch_from_main("feature/read")
        test_file = Path(temp_git_repo) / "branch-file.txt"
        test_file.write_text("branch content")
        git_ops.commit_changes("Add branch file")

        # Read from branch
        content = git_ops.get_file_content("branch-file.txt", branch="feature/read")
        assert content == "branch content"

    def test_get_file_content_not_found(self, temp_git_repo):
        """Test reading nonexistent file."""
        git_ops = GitOperations(temp_git_repo)

        with pytest.raises(FileNotFoundError):
            git_ops.get_file_content("nonexistent.txt")

    def test_write_file_content(self, temp_git_repo):
        """Test writing file content."""
        git_ops = GitOperations(temp_git_repo)

        git_ops.write_file_content("new-file.txt", "new content")

        # Verify
        file_path = Path(temp_git_repo) / "new-file.txt"
        assert file_path.read_text() == "new content"

    def test_write_file_creates_directories(self, temp_git_repo):
        """Test that writing creates parent directories."""
        git_ops = GitOperations(temp_git_repo)

        git_ops.write_file_content("nested/dir/file.txt", "nested content")

        file_path = Path(temp_git_repo) / "nested" / "dir" / "file.txt"
        assert file_path.exists()
        assert file_path.read_text() == "nested content"


class TestConflictDetection:
    """Test merge conflict detection."""

    def test_test_merge_conflict_no_conflict(self, temp_git_repo):
        """Test detecting no conflict."""
        git_ops = GitOperations(temp_git_repo)

        # Create non-conflicting branch
        git_ops.create_branch_from_main("feature/no-conflict")
        (Path(temp_git_repo) / "no-conflict.txt").write_text("content")
        git_ops.commit_changes("Add file")

        has_conflict, files = git_ops.test_merge_conflict("feature/no-conflict")
        assert has_conflict is False
        assert files == []

    def test_get_conflict_markers(self, temp_git_repo):
        """Test reading conflict markers from a file."""
        git_ops = GitOperations(temp_git_repo)

        # Create file with conflict markers
        conflict_file = Path(temp_git_repo) / "conflicted.txt"
        conflict_file.write_text("""<<<<<<< HEAD
version A
=======
version B
>>>>>>> feature
""")

        content = git_ops.get_conflict_markers("conflicted.txt")
        assert "<<<<<<<" in content
        assert "=======" in content
        assert ">>>>>>>" in content
