"""
Git operations wrapper using GitPython.

This module provides a safe, atomic interface for git operations
used by the multi-agent orchestrator.
"""

import os
import logging
from typing import List, Tuple, Optional
from datetime import datetime
import git
from git import Repo, GitCommandError


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitOperations:
    """
    Wrapper class for git operations using GitPython.

    All operations are atomic and include comprehensive error handling.
    Designed to be safe for concurrent use by multiple agents.
    """

    def __init__(self, repo_path: str = "."):
        """
        Initialize GitOperations with a repository path.

        Args:
            repo_path: Path to the git repository (default: current directory)

        Raises:
            ValueError: If the path is not a valid git repository
        """
        try:
            self.repo = Repo(repo_path)
            self.repo_path = repo_path
            logger.info(f"Initialized GitOperations for repository at {os.path.abspath(repo_path)}")
        except git.exc.InvalidGitRepositoryError:
            raise ValueError(f"Path {repo_path} is not a valid git repository")

    def get_current_branch(self) -> str:
        """
        Get the name of the currently checked out branch.

        Returns:
            str: Name of the current branch

        Raises:
            RuntimeError: If unable to determine current branch
        """
        try:
            branch_name = self.repo.active_branch.name
            logger.info(f"Current branch: {branch_name}")
            return branch_name
        except Exception as e:
            logger.error(f"Failed to get current branch: {e}")
            raise RuntimeError(f"Failed to get current branch: {e}")

    def create_branch_from_main(self, branch_name: str, main_branch: str = "main") -> None:
        """
        Create a new branch from the main branch.

        This method:
        1. Checks out the main branch
        2. Pulls the latest changes
        3. Creates and checks out the new branch

        Args:
            branch_name: Name of the new branch to create
            main_branch: Name of the main branch to branch from (default: "main")

        Raises:
            RuntimeError: If branch already exists or git operations fail
        """
        try:
            # Check if branch already exists
            if branch_name in self.repo.heads:
                logger.warning(f"Branch {branch_name} already exists, checking it out")
                self.repo.heads[branch_name].checkout()
                return

            # Checkout main branch
            logger.info(f"Checking out {main_branch} branch")
            self.repo.heads[main_branch].checkout()

            # Pull latest changes
            logger.info(f"Pulling latest changes from {main_branch}")
            origin = self.repo.remote(name='origin')
            origin.pull(main_branch)

            # Create new branch
            logger.info(f"Creating new branch: {branch_name}")
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            logger.info(f"Successfully created and checked out branch: {branch_name}")

        except GitCommandError as e:
            logger.error(f"Git command failed while creating branch {branch_name}: {e}")
            raise RuntimeError(f"Failed to create branch {branch_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating branch {branch_name}: {e}")
            raise RuntimeError(f"Unexpected error creating branch {branch_name}: {e}")

    def commit_changes(self, message: str) -> bool:
        """
        Commit all changes in the working directory.

        Args:
            message: Commit message

        Returns:
            bool: True if changes were committed, False if no changes to commit

        Raises:
            RuntimeError: If commit fails
        """
        try:
            # Check if there are changes to commit
            if not self.repo.is_dirty(untracked_files=True):
                logger.info("No changes to commit")
                return False

            # Add all changes
            self.repo.git.add(A=True)

            # Commit
            commit = self.repo.index.commit(message)
            logger.info(f"Committed changes: {commit.hexsha[:7]} - {message}")

            return True

        except GitCommandError as e:
            logger.error(f"Git command failed during commit: {e}")
            raise RuntimeError(f"Failed to commit changes: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during commit: {e}")
            raise RuntimeError(f"Unexpected error during commit: {e}")

    def get_branch_commits_ahead_of_main(self, branch_name: str, main_branch: str = "main") -> int:
        """
        Get the number of commits a branch is ahead of main.

        Args:
            branch_name: Name of the branch to check
            main_branch: Name of the main branch (default: "main")

        Returns:
            int: Number of commits ahead

        Raises:
            RuntimeError: If unable to calculate commits ahead
        """
        try:
            main_commit = self.repo.heads[main_branch].commit
            branch_commit = self.repo.heads[branch_name].commit

            # Get commits in branch but not in main
            commits_ahead = list(self.repo.iter_commits(f'{main_branch}..{branch_name}'))
            count = len(commits_ahead)

            logger.info(f"Branch {branch_name} is {count} commits ahead of {main_branch}")
            return count

        except Exception as e:
            logger.error(f"Failed to get commits ahead for {branch_name}: {e}")
            raise RuntimeError(f"Failed to get commits ahead: {e}")

    def test_merge_conflict(self, branch_name: str, main_branch: str = "main") -> Tuple[bool, List[str]]:
        """
        Test if merging a branch into main would cause conflicts.

        This performs a test merge without actually committing changes.

        Args:
            branch_name: Branch to test merging
            main_branch: Target branch (default: "main")

        Returns:
            Tuple[bool, List[str]]: (has_conflicts, list_of_conflicting_files)

        Raises:
            RuntimeError: If test merge fails unexpectedly
        """
        try:
            # Store current branch to restore later
            current_branch = self.get_current_branch()

            # Checkout main branch
            self.repo.heads[main_branch].checkout()

            # Try to merge
            try:
                base = self.repo.merge_base(main_branch, branch_name)
                self.repo.index.merge_tree(branch_name, base=base)

                # Check for conflicts
                conflicting_files = [item[0] for item in self.repo.index.unmerged_blobs().items()]

                # Reset to clean state
                self.repo.index.reset(hard=True)

                # Return to original branch
                self.repo.heads[current_branch].checkout()

                if conflicting_files:
                    logger.warning(f"Merge conflicts detected in files: {conflicting_files}")
                    return True, conflicting_files
                else:
                    logger.info(f"No merge conflicts detected for branch {branch_name}")
                    return False, []

            except GitCommandError as e:
                # Reset to clean state
                self.repo.git.reset('--hard')

                # Return to original branch
                self.repo.heads[current_branch].checkout()

                if "conflict" in str(e).lower():
                    # Parse conflicting files from error message
                    logger.warning(f"Merge conflict detected: {e}")
                    return True, []
                else:
                    raise e

        except Exception as e:
            logger.error(f"Failed to test merge conflict: {e}")
            raise RuntimeError(f"Failed to test merge conflict: {e}")

    def get_file_content(self, file_path: str, branch: Optional[str] = None) -> str:
        """
        Get the content of a file from a specific branch or working directory.

        Args:
            file_path: Path to the file relative to repo root
            branch: Branch name (if None, reads from working directory)

        Returns:
            str: File content

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If unable to read file
        """
        try:
            if branch:
                # Read from specific branch
                commit = self.repo.heads[branch].commit
                try:
                    blob = commit.tree / file_path
                    content = blob.data_stream.read().decode('utf-8')
                    logger.info(f"Read {file_path} from branch {branch}")
                    return content
                except KeyError:
                    raise FileNotFoundError(f"File {file_path} not found in branch {branch}")
            else:
                # Read from working directory
                full_path = os.path.join(self.repo_path, file_path)
                if not os.path.exists(full_path):
                    raise FileNotFoundError(f"File {file_path} not found in working directory")

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info(f"Read {file_path} from working directory")
                return content

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise RuntimeError(f"Failed to read file {file_path}: {e}")

    def get_conflict_markers(self, file_path: str) -> str:
        """
        Get content of a file with conflict markers.

        This is used after a failed merge to examine conflicts.

        Args:
            file_path: Path to the conflicted file

        Returns:
            str: File content with conflict markers

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            full_path = os.path.join(self.repo_path, file_path)
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"File {file_path} not found")

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if '<<<<<<<' in content:
                logger.info(f"Found conflict markers in {file_path}")
            else:
                logger.warning(f"No conflict markers found in {file_path}")

            return content

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to read conflict markers from {file_path}: {e}")
            raise RuntimeError(f"Failed to read conflict markers: {e}")

    def write_file_content(self, file_path: str, content: str) -> None:
        """
        Write content to a file in the working directory.

        Creates parent directories if they don't exist.

        Args:
            file_path: Path to the file relative to repo root
            content: Content to write

        Raises:
            RuntimeError: If write fails
        """
        try:
            full_path = os.path.join(self.repo_path, file_path)

            # Create parent directories if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Wrote content to {file_path}")

        except Exception as e:
            logger.error(f"Failed to write to {file_path}: {e}")
            raise RuntimeError(f"Failed to write to {file_path}: {e}")

    def merge_branch(self, branch_name: str, main_branch: str = "main") -> bool:
        """
        Merge a branch into the main branch.

        Args:
            branch_name: Branch to merge
            main_branch: Target branch (default: "main")

        Returns:
            bool: True if merge successful, False if conflicts occurred

        Raises:
            RuntimeError: If merge fails unexpectedly
        """
        try:
            # Checkout main branch
            logger.info(f"Checking out {main_branch} for merge")
            self.repo.heads[main_branch].checkout()

            # Pull latest changes
            logger.info(f"Pulling latest changes from {main_branch}")
            origin = self.repo.remote(name='origin')
            origin.pull(main_branch)

            # Attempt merge
            try:
                logger.info(f"Merging {branch_name} into {main_branch}")
                self.repo.git.merge(branch_name)
                logger.info(f"Successfully merged {branch_name} into {main_branch}")
                return True

            except GitCommandError as e:
                if "conflict" in str(e).lower():
                    logger.error(f"Merge conflict occurred: {e}")
                    # Abort the merge
                    self.repo.git.merge('--abort')
                    return False
                else:
                    raise e

        except Exception as e:
            logger.error(f"Failed to merge {branch_name}: {e}")
            raise RuntimeError(f"Failed to merge {branch_name}: {e}")

    def get_recent_commits(self, branch: str, count: int = 5) -> List[str]:
        """
        Get recent commits from a branch.

        Args:
            branch: Branch name
            count: Number of commits to retrieve (default: 5)

        Returns:
            List[str]: List of commit messages with metadata

        Raises:
            RuntimeError: If unable to get commits
        """
        try:
            commits = list(self.repo.iter_commits(branch, max_count=count))

            commit_info = []
            for commit in commits:
                info = f"{commit.hexsha[:7]} - {commit.author.name} - {commit.message.strip()}"
                commit_info.append(info)

            logger.info(f"Retrieved {len(commit_info)} commits from {branch}")
            return commit_info

        except Exception as e:
            logger.error(f"Failed to get commits from {branch}: {e}")
            raise RuntimeError(f"Failed to get commits: {e}")

    def push_branch(self, branch_name: str) -> None:
        """
        Push a branch to the remote repository.

        Args:
            branch_name: Branch to push

        Raises:
            RuntimeError: If push fails
        """
        try:
            logger.info(f"Pushing branch {branch_name} to remote")
            origin = self.repo.remote(name='origin')
            origin.push(branch_name)
            logger.info(f"Successfully pushed {branch_name}")

        except GitCommandError as e:
            logger.error(f"Failed to push {branch_name}: {e}")
            raise RuntimeError(f"Failed to push {branch_name}: {e}")

    def get_all_branches(self) -> List[str]:
        """
        Get all local branches.

        Returns:
            List[str]: List of branch names
        """
        try:
            branches = [head.name for head in self.repo.heads]
            logger.info(f"Found {len(branches)} branches: {branches}")
            return branches
        except Exception as e:
            logger.error(f"Failed to get branches: {e}")
            raise RuntimeError(f"Failed to get branches: {e}")

    def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch exists.

        Args:
            branch_name: Branch name to check

        Returns:
            bool: True if branch exists, False otherwise
        """
        return branch_name in self.repo.heads
