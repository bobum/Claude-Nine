"""
Git operations wrapper using GitPython with Worktree support.

This module provides a safe, atomic interface for git operations
used by the multi-agent orchestrator. It uses git worktrees to enable
multiple agents to work in parallel on different branches without conflicts.
"""

import os
import shutil
import logging
from typing import List, Tuple, Optional, Dict
from pathlib import Path
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
    Wrapper class for git operations using GitPython with worktree support.

    All operations are atomic and include comprehensive error handling.
    Designed to be safe for concurrent use by multiple agents using worktrees.

    Worktrees allow multiple working directories from the same repository,
    enabling true parallel development on different branches.
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
            self.repo_path = os.path.abspath(repo_path)
            logger.info(f"Initialized GitOperations for repository at {self.repo_path}")
        except git.exc.InvalidGitRepositoryError:
            raise ValueError(f"Path {repo_path} is not a valid git repository")

    def create_worktree(self, branch_name: str, worktree_path: str, main_branch: str = "main") -> str:
        """
        Create a git worktree for isolated parallel work.

        A worktree is a separate working directory linked to the same repository.
        This allows multiple agents to work on different branches simultaneously
        without interfering with each other.

        Args:
            branch_name: Name of the branch for this worktree
            worktree_path: Path where the worktree should be created
            main_branch: Base branch to create new branch from (default: "main")

        Returns:
            str: Absolute path to the created worktree

        Raises:
            RuntimeError: If worktree creation fails
        """
        try:
            worktree_abs_path = os.path.abspath(worktree_path)

            # Check if worktree path already exists
            if os.path.exists(worktree_abs_path):
                logger.warning(f"Worktree path {worktree_abs_path} already exists, removing it first")
                shutil.rmtree(worktree_abs_path)

            # Fetch latest changes to ensure we have the latest main
            logger.info(f"Fetching latest changes from origin")
            try:
                origin = self.repo.remote(name='origin')
                origin.fetch()
            except Exception as e:
                logger.warning(f"Could not fetch from origin: {e}")

            # Check if branch already exists
            if branch_name in self.repo.heads:
                logger.info(f"Branch {branch_name} already exists, creating worktree from existing branch")
                self.repo.git.worktree('add', worktree_abs_path, branch_name)
            else:
                # Create new branch from main in the worktree
                logger.info(f"Creating new branch {branch_name} from {main_branch} in worktree")
                self.repo.git.worktree('add', '-b', branch_name, worktree_abs_path, main_branch)

            logger.info(f"Created worktree at {worktree_abs_path} for branch {branch_name}")
            return worktree_abs_path

        except GitCommandError as e:
            logger.error(f"Git command failed while creating worktree: {e}")
            raise RuntimeError(f"Failed to create worktree for {branch_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating worktree: {e}")
            raise RuntimeError(f"Unexpected error creating worktree: {e}")

    def remove_worktree(self, worktree_path: str, force: bool = False) -> None:
        """
        Remove a git worktree.

        Args:
            worktree_path: Path to the worktree to remove
            force: Force removal even if worktree has uncommitted changes

        Raises:
            RuntimeError: If worktree removal fails
        """
        try:
            worktree_abs_path = os.path.abspath(worktree_path)

            if not os.path.exists(worktree_abs_path):
                logger.warning(f"Worktree {worktree_abs_path} does not exist, skipping removal")
                return

            # Remove the worktree
            if force:
                self.repo.git.worktree('remove', '--force', worktree_abs_path)
            else:
                self.repo.git.worktree('remove', worktree_abs_path)

            logger.info(f"Removed worktree at {worktree_abs_path}")

        except GitCommandError as e:
            logger.error(f"Git command failed while removing worktree: {e}")
            # Try to clean up the directory manually if git command fails
            try:
                if os.path.exists(worktree_abs_path):
                    shutil.rmtree(worktree_abs_path)
                    # Prune stale worktree references
                    self.repo.git.worktree('prune')
                    logger.info(f"Manually removed worktree directory and pruned references")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up worktree: {cleanup_error}")
            raise RuntimeError(f"Failed to remove worktree: {e}")
        except Exception as e:
            logger.error(f"Unexpected error removing worktree: {e}")
            raise RuntimeError(f"Unexpected error removing worktree: {e}")

    def list_worktrees(self) -> List[Dict[str, str]]:
        """
        List all worktrees in the repository.

        Returns:
            List[Dict[str, str]]: List of worktree information dictionaries
                Each dict contains: 'path', 'branch', 'commit'

        Raises:
            RuntimeError: If listing worktrees fails
        """
        try:
            # Get worktree list output
            output = self.repo.git.worktree('list', '--porcelain')

            worktrees = []
            current_worktree = {}

            for line in output.split('\n'):
                if line.startswith('worktree '):
                    if current_worktree:
                        worktrees.append(current_worktree)
                    current_worktree = {'path': line.split(' ', 1)[1]}
                elif line.startswith('branch '):
                    current_worktree['branch'] = line.split('refs/heads/', 1)[1] if 'refs/heads/' in line else 'detached'
                elif line.startswith('HEAD '):
                    current_worktree['commit'] = line.split(' ', 1)[1]

            if current_worktree:
                worktrees.append(current_worktree)

            logger.info(f"Found {len(worktrees)} worktrees")
            return worktrees

        except GitCommandError as e:
            logger.error(f"Failed to list worktrees: {e}")
            raise RuntimeError(f"Failed to list worktrees: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing worktrees: {e}")
            raise RuntimeError(f"Unexpected error listing worktrees: {e}")

    def cleanup_all_worktrees(self, workspace_dir: str) -> None:
        """
        Clean up all worktrees in the workspace directory.

        Args:
            workspace_dir: Directory containing worktrees to clean up

        Raises:
            RuntimeError: If cleanup fails
        """
        try:
            workspace_path = Path(workspace_dir)

            if not workspace_path.exists():
                logger.info(f"Workspace directory {workspace_dir} does not exist, nothing to clean up")
                return

            # Get all worktrees
            worktrees = self.list_worktrees()

            # Remove each worktree that's in the workspace directory
            for worktree in worktrees:
                worktree_path = worktree['path']
                if workspace_dir in worktree_path:
                    logger.info(f"Cleaning up worktree at {worktree_path}")
                    self.remove_worktree(worktree_path, force=True)

            # Prune stale worktree references
            self.repo.git.worktree('prune')

            logger.info("All worktrees cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during worktree cleanup: {e}")
            raise RuntimeError(f"Failed to cleanup worktrees: {e}")

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

        Note: When using worktrees, prefer create_worktree() instead.
        This method is kept for compatibility with the monitor agent.

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
            try:
                origin = self.repo.remote(name='origin')
                origin.pull(main_branch)
            except Exception as e:
                logger.warning(f"Could not pull from origin: {e}")

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
            parent_dir = os.path.dirname(full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

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
            try:
                origin = self.repo.remote(name='origin')
                origin.pull(main_branch)
            except Exception as e:
                logger.warning(f"Could not pull from origin: {e}")

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

    def merge_branches_into_integration(
        self,
        feature_branches: List[str],
        main_branch: str = "main",
        integration_branch: str = None
    ) -> Dict[str, any]:
        """
        Merge multiple feature branches into a single integration branch.

        Creates an integration branch from main, then merges each feature branch
        sequentially. If any merge fails due to conflicts, stops and returns
        conflict info for the resolver agent.

        Args:
            feature_branches: List of feature branch names to merge
            main_branch: Base branch to create integration from (default: "main")
            integration_branch: Name for integration branch (auto-generated if None)

        Returns:
            Dict with keys:
                - success: bool - True if all merges succeeded
                - integration_branch: str - Name of the integration branch
                - merged_branches: List[str] - Branches that were successfully merged
                - failed_branch: str or None - Branch that caused conflict
                - conflicting_files: List[str] - Files with conflicts (if any)
        """
        result = {
            "success": False,
            "integration_branch": None,
            "merged_branches": [],
            "failed_branch": None,
            "conflicting_files": []
        }

        try:
            # Generate integration branch name if not provided
            if not integration_branch:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                integration_branch = f"integration/{timestamp}"

            result["integration_branch"] = integration_branch

            # Checkout main branch first
            logger.info(f"Checking out {main_branch} to create integration branch")
            self.repo.heads[main_branch].checkout()

            # Pull latest main
            try:
                origin = self.repo.remote(name='origin')
                origin.pull(main_branch)
            except Exception as e:
                logger.warning(f"Could not pull from origin: {e}")

            # Create integration branch from main
            if integration_branch in self.repo.heads:
                logger.warning(f"Integration branch {integration_branch} already exists, deleting it")
                self.repo.delete_head(integration_branch, force=True)

            logger.info(f"Creating integration branch: {integration_branch}")
            new_branch = self.repo.create_head(integration_branch)
            new_branch.checkout()

            # Merge each feature branch sequentially
            for branch in feature_branches:
                if not self.branch_exists(branch):
                    logger.warning(f"Branch {branch} does not exist, skipping")
                    continue

                try:
                    logger.info(f"Merging {branch} into {integration_branch}")
                    self.repo.git.merge(branch, m=f"Merge {branch} into {integration_branch}")
                    result["merged_branches"].append(branch)
                    logger.info(f"Successfully merged {branch}")

                except GitCommandError as e:
                    if "conflict" in str(e).lower() or "CONFLICT" in str(e):
                        logger.error(f"Merge conflict while merging {branch}: {e}")
                        result["failed_branch"] = branch

                        # Get conflicting files
                        try:
                            status_output = self.repo.git.status('--porcelain')
                            conflicting = []
                            for line in status_output.split('\n'):
                                if line.startswith('UU ') or line.startswith('AA '):
                                    conflicting.append(line[3:])
                            result["conflicting_files"] = conflicting
                        except Exception:
                            pass

                        # Abort the merge
                        try:
                            self.repo.git.merge('--abort')
                        except Exception:
                            pass

                        logger.error(f"Merge failed at branch {branch}, aborting")
                        return result
                    else:
                        raise e

            # All merges succeeded
            result["success"] = True
            logger.info(f"Successfully merged all {len(result['merged_branches'])} branches into {integration_branch}")
            return result

        except Exception as e:
            logger.error(f"Unexpected error during integration merge: {e}")
            result["failed_branch"] = "unknown"
            return result

    def start_merge_with_conflicts(
        self,
        branch_name: str,
        allow_conflicts: bool = True
    ) -> Dict[str, any]:
        """
        Start a merge that may have conflicts, without aborting.

        Unlike regular merge, this leaves conflicting files with conflict markers
        for manual or automated resolution.

        Args:
            branch_name: Branch to merge into current branch
            allow_conflicts: If True, don't abort on conflicts

        Returns:
            Dict with keys:
                - success: bool - True if merge completed without conflicts
                - has_conflicts: bool - True if there are unresolved conflicts
                - conflicting_files: List[str] - Files with conflicts
        """
        result = {
            "success": False,
            "has_conflicts": False,
            "conflicting_files": []
        }

        try:
            logger.info(f"Starting merge of {branch_name} (allow_conflicts={allow_conflicts})")
            self.repo.git.merge(branch_name, no_commit=True)
            result["success"] = True
            logger.info(f"Merge of {branch_name} completed without conflicts")

        except GitCommandError as e:
            if "conflict" in str(e).lower() or "CONFLICT" in str(e):
                logger.warning(f"Merge has conflicts: {e}")
                result["has_conflicts"] = True

                # Get list of conflicting files
                try:
                    status_output = self.repo.git.status('--porcelain')
                    for line in status_output.split('\n'):
                        if line.startswith('UU ') or line.startswith('AA ') or line.startswith('DU ') or line.startswith('UD '):
                            result["conflicting_files"].append(line[3:].strip())
                except Exception:
                    pass

                if not allow_conflicts:
                    logger.info("Aborting merge due to conflicts")
                    self.repo.git.merge('--abort')
            else:
                raise

        return result

    def get_conflict_content(self, file_path: str) -> Dict[str, str]:
        """
        Get the conflicting content from a file with conflict markers.

        Args:
            file_path: Path to the conflicted file

        Returns:
            Dict with keys:
                - full_content: str - The file with conflict markers
                - ours: str - Our version (current branch)
                - theirs: str - Their version (merging branch)
                - base: str - Common ancestor (if available)
        """
        full_path = os.path.join(self.repo_path, file_path)

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = {
            "full_content": content,
            "ours": "",
            "theirs": "",
            "base": ""
        }

        # Parse conflict markers
        # Format: <<<<<<< HEAD ... ||||||| base ... ======= ... >>>>>>> branch
        import re

        # Simple two-way conflict
        two_way = re.findall(
            r'<<<<<<<[^\n]*\n(.*?)\n=======\n(.*?)\n>>>>>>>[^\n]*',
            content,
            re.DOTALL
        )

        if two_way:
            result["ours"] = "\n---\n".join([m[0] for m in two_way])
            result["theirs"] = "\n---\n".join([m[1] for m in two_way])

        return result

    def resolve_conflict(self, file_path: str, resolved_content: str) -> None:
        """
        Resolve a conflict by writing the resolved content and staging the file.

        Args:
            file_path: Path to the conflicted file
            resolved_content: The resolved content to write
        """
        full_path = os.path.join(self.repo_path, file_path)

        # Write resolved content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(resolved_content)

        # Stage the file
        self.repo.index.add([file_path])
        logger.info(f"Resolved and staged: {file_path}")

    def complete_merge(self, message: str) -> bool:
        """
        Complete a merge after all conflicts are resolved.

        Args:
            message: Commit message for the merge

        Returns:
            bool: True if merge was completed successfully
        """
        try:
            # Check if there are still unmerged files
            status = self.repo.git.status('--porcelain')
            for line in status.split('\n'):
                if line.startswith('UU ') or line.startswith('AA '):
                    logger.error(f"Cannot complete merge - unresolved conflicts remain")
                    return False

            # Commit the merge
            self.repo.index.commit(message)
            logger.info(f"Merge completed with message: {message}")
            return True

        except Exception as e:
            logger.error(f"Failed to complete merge: {e}")
            return False

    def abort_merge(self) -> None:
        """Abort the current merge in progress."""
        try:
            self.repo.git.merge('--abort')
            logger.info("Merge aborted")
        except Exception as e:
            logger.warning(f"Could not abort merge: {e}")

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """
        Delete a local branch.

        Args:
            branch_name: Branch name to delete
            force: Force delete even if not fully merged

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            if not self.branch_exists(branch_name):
                logger.warning(f"Branch {branch_name} does not exist")
                return

            logger.info(f"Deleting branch {branch_name}")
            self.repo.delete_head(branch_name, force=force)
            logger.info(f"Successfully deleted branch {branch_name}")

        except GitCommandError as e:
            logger.error(f"Failed to delete branch {branch_name}: {e}")
            raise RuntimeError(f"Failed to delete branch {branch_name}: {e}")
