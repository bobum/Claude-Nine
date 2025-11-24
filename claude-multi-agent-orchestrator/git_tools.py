"""
CrewAI tools for git operations.

This module provides BaseTool subclasses that wrap git_operations
for use by CrewAI agents.
"""

from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai_tools import BaseTool
from git_operations import GitOperations
import logging


logger = logging.getLogger(__name__)


class CreateBranchInput(BaseModel):
    """Input schema for CreateBranchTool."""
    branch_name: str = Field(..., description="Name of the new branch to create")
    main_branch: str = Field(default="main", description="Name of the main branch to branch from")


class CreateBranchTool(BaseTool):
    name: str = "Create Git Branch"
    description: str = (
        "Creates a new git branch from the main branch. "
        "This tool automatically checks out main, pulls the latest changes, "
        "and creates a new branch. Use this at the start of working on a new feature. "
        "Input: branch_name (required), main_branch (optional, default='main')"
    )
    args_schema: Type[BaseModel] = CreateBranchInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, branch_name: str, main_branch: str = "main") -> str:
        """Create a new branch from main."""
        try:
            self.git_ops.create_branch_from_main(branch_name, main_branch)
            return f"Successfully created and checked out branch: {branch_name}"
        except Exception as e:
            return f"Error creating branch: {str(e)}"


class CommitChangesInput(BaseModel):
    """Input schema for CommitChangesTool."""
    message: str = Field(..., description="Commit message describing the changes")


class CommitChangesTool(BaseTool):
    name: str = "Commit Changes"
    description: str = (
        "Commits all changes in the working directory with a commit message. "
        "This tool adds all modified and new files and creates a commit. "
        "Use this after making changes to save your progress. "
        "Input: message (required) - a descriptive commit message"
    )
    args_schema: Type[BaseModel] = CommitChangesInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, message: str) -> str:
        """Commit all changes with a message."""
        try:
            committed = self.git_ops.commit_changes(message)
            if committed:
                return f"Successfully committed changes: {message}"
            else:
                return "No changes to commit"
        except Exception as e:
            return f"Error committing changes: {str(e)}"


class WriteFileInput(BaseModel):
    """Input schema for WriteFileTool."""
    file_path: str = Field(..., description="Path to the file relative to repository root")
    content: str = Field(..., description="Content to write to the file")


class WriteFileTool(BaseTool):
    name: str = "Write File"
    description: str = (
        "Writes content to a file in the repository. "
        "Creates parent directories if they don't exist. "
        "Use this to create new files or modify existing ones. "
        "Input: file_path (required) - relative path from repo root, "
        "content (required) - file content"
    )
    args_schema: Type[BaseModel] = WriteFileInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, file_path: str, content: str) -> str:
        """Write content to a file."""
        try:
            self.git_ops.write_file_content(file_path, content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"


class ReadFileInput(BaseModel):
    """Input schema for ReadFileTool."""
    file_path: str = Field(..., description="Path to the file relative to repository root")
    branch: Optional[str] = Field(default=None, description="Branch to read from (None for working directory)")


class ReadFileTool(BaseTool):
    name: str = "Read File"
    description: str = (
        "Reads the content of a file from the working directory or a specific branch. "
        "Use this to examine existing code before making changes or to compare versions. "
        "Input: file_path (required) - relative path from repo root, "
        "branch (optional) - branch name to read from, None for current working directory"
    )
    args_schema: Type[BaseModel] = ReadFileInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, file_path: str, branch: Optional[str] = None) -> str:
        """Read content from a file."""
        try:
            content = self.git_ops.get_file_content(file_path, branch)
            return f"Content of {file_path}:\n\n{content}"
        except FileNotFoundError:
            return f"File {file_path} not found"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class CheckConflictsInput(BaseModel):
    """Input schema for CheckConflictsTool."""
    branch_name: str = Field(..., description="Branch to check for conflicts")
    main_branch: str = Field(default="main", description="Target branch to merge into")


class CheckConflictsTool(BaseTool):
    name: str = "Check Merge Conflicts"
    description: str = (
        "Tests if merging a branch into main would cause conflicts. "
        "This performs a test merge without actually committing changes. "
        "Use this before attempting to merge to detect potential conflicts. "
        "Input: branch_name (required) - branch to test, "
        "main_branch (optional, default='main') - target branch"
    )
    args_schema: Type[BaseModel] = CheckConflictsInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, branch_name: str, main_branch: str = "main") -> str:
        """Check for merge conflicts."""
        try:
            has_conflicts, conflicting_files = self.git_ops.test_merge_conflict(branch_name, main_branch)
            if has_conflicts:
                if conflicting_files:
                    files_str = ", ".join(conflicting_files)
                    return f"Merge conflicts detected in files: {files_str}"
                else:
                    return "Merge conflicts detected (files could not be determined)"
            else:
                return f"No merge conflicts detected. Branch {branch_name} can be safely merged."
        except Exception as e:
            return f"Error checking conflicts: {str(e)}"


class MergeBranchInput(BaseModel):
    """Input schema for MergeBranchTool."""
    branch_name: str = Field(..., description="Branch to merge")
    main_branch: str = Field(default="main", description="Target branch to merge into")


class MergeBranchTool(BaseTool):
    name: str = "Merge Branch"
    description: str = (
        "Merges a branch into the main branch. "
        "This checks out main, pulls latest changes, and attempts the merge. "
        "If conflicts occur, the merge is aborted. "
        "Use this after verifying no conflicts exist. "
        "Input: branch_name (required) - branch to merge, "
        "main_branch (optional, default='main') - target branch"
    )
    args_schema: Type[BaseModel] = MergeBranchInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, branch_name: str, main_branch: str = "main") -> str:
        """Merge a branch into main."""
        try:
            success = self.git_ops.merge_branch(branch_name, main_branch)
            if success:
                return f"Successfully merged {branch_name} into {main_branch}"
            else:
                return f"Merge failed due to conflicts. Please resolve conflicts first."
        except Exception as e:
            return f"Error merging branch: {str(e)}"


class GetBranchesInput(BaseModel):
    """Input schema for GetBranchesTool."""
    pass


class GetBranchesTool(BaseTool):
    name: str = "Get Branches"
    description: str = (
        "Lists all local git branches in the repository. "
        "Use this to see what feature branches exist and monitor ongoing work. "
        "No input required."
    )
    args_schema: Type[BaseModel] = GetBranchesInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self) -> str:
        """Get all branches."""
        try:
            branches = self.git_ops.get_all_branches()
            return f"Branches: {', '.join(branches)}"
        except Exception as e:
            return f"Error getting branches: {str(e)}"


class GetRecentCommitsInput(BaseModel):
    """Input schema for GetRecentCommitsTool."""
    branch: str = Field(..., description="Branch to get commits from")
    count: int = Field(default=5, description="Number of commits to retrieve")


class GetRecentCommitsTool(BaseTool):
    name: str = "Get Recent Commits"
    description: str = (
        "Gets recent commit history from a branch. "
        "Returns commit hashes, authors, and messages. "
        "Use this to see what work has been done on a branch. "
        "Input: branch (required) - branch name, "
        "count (optional, default=5) - number of commits"
    )
    args_schema: Type[BaseModel] = GetRecentCommitsInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, branch: str, count: int = 5) -> str:
        """Get recent commits from a branch."""
        try:
            commits = self.git_ops.get_recent_commits(branch, count)
            return f"Recent commits on {branch}:\n" + "\n".join(commits)
        except Exception as e:
            return f"Error getting commits: {str(e)}"


class PushBranchInput(BaseModel):
    """Input schema for PushBranchTool."""
    branch_name: str = Field(..., description="Branch to push to remote")


class PushBranchTool(BaseTool):
    name: str = "Push Branch"
    description: str = (
        "Pushes a branch to the remote repository. "
        "Use this after committing changes to make them visible to other agents. "
        "Input: branch_name (required) - name of branch to push"
    )
    args_schema: Type[BaseModel] = PushBranchInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self, branch_name: str) -> str:
        """Push a branch to remote."""
        try:
            self.git_ops.push_branch(branch_name)
            return f"Successfully pushed {branch_name} to remote"
        except Exception as e:
            return f"Error pushing branch: {str(e)}"


class GetCurrentBranchInput(BaseModel):
    """Input schema for GetCurrentBranchTool."""
    pass


class GetCurrentBranchTool(BaseTool):
    name: str = "Get Current Branch"
    description: str = (
        "Gets the name of the currently checked out branch. "
        "Use this to verify which branch you're working on. "
        "No input required."
    )
    args_schema: Type[BaseModel] = GetCurrentBranchInput

    def __init__(self, git_ops: GitOperations):
        super().__init__()
        self.git_ops = git_ops

    def _run(self) -> str:
        """Get current branch name."""
        try:
            branch = self.git_ops.get_current_branch()
            return f"Current branch: {branch}"
        except Exception as e:
            return f"Error getting current branch: {str(e)}"


def create_git_tools(repo_path: str = ".") -> list:
    """
    Create all git tools for a repository.

    Args:
        repo_path: Path to the git repository

    Returns:
        list: List of all git tool instances
    """
    git_ops = GitOperations(repo_path)

    tools = [
        CreateBranchTool(git_ops),
        CommitChangesTool(git_ops),
        WriteFileTool(git_ops),
        ReadFileTool(git_ops),
        CheckConflictsTool(git_ops),
        MergeBranchTool(git_ops),
        GetBranchesTool(git_ops),
        GetRecentCommitsTool(git_ops),
        PushBranchTool(git_ops),
        GetCurrentBranchTool(git_ops),
    ]

    logger.info(f"Created {len(tools)} git tools for repository at {repo_path}")
    return tools
