#!/usr/bin/env python3
"""
Multi-Agent Orchestrator for CrewAI with Claude.

This orchestrator manages multiple Claude agents working simultaneously
on different features in a monorepo.

Uses git worktrees to give each agent an isolated working directory,
enabling true parallel development without interference.

Post-completion merge phase handles branch merging after all tasks complete.
"""

import os
import sys
import time
import yaml
import logging
import signal
import atexit
import subprocess
import requests
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path

from crewai import Agent, Task, Crew, Process, LLM
from git_tools import create_git_tools
from git_operations import GitOperations
from telemetry_collector import (
    initialize_telemetry,
    get_telemetry_collector,
    shutdown_telemetry
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orchestrates multiple Claude agents working on different features in parallel.

    Features:
    - Parallel feature development on separate branches using git worktrees
    - Each agent gets its own isolated working directory
    - Post-completion merge phase for combining branches
    - Automatic cleanup of worktrees on shutdown
    """

    def __init__(self, config_path: str = "config.yaml", tasks_path: str = "tasks/example_tasks.yaml", team_id: str = None):
        """
        Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
            tasks_path: Path to tasks definition file
            team_id: Team ID for API integration (optional)
        """
        self.config = self._load_config(config_path)
        self.tasks_config = self._load_tasks(tasks_path)
        self.repo_path = os.getcwd()

        # Main git operations (for coordination)
        self.git_ops = GitOperations(self.repo_path)

        # Workspace directory for worktrees and logs
        self.workspace_dir = Path(".agent-workspace")
        self.workspace_dir.mkdir(exist_ok=True)

        # Configure file logging after workspace is created
        file_handler = logging.FileHandler(self.workspace_dir / 'orchestrator.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)

        # Track worktrees for cleanup
        self.worktrees: List[str] = []
        # Track branches created for post-completion merge
        self.feature_branches: List[str] = []
        self.running = True

        # Telemetry
        self.team_id = team_id

        # Set up API key
        if 'anthropic_api_key' in self.config and self.config['anthropic_api_key']:
            os.environ['ANTHROPIC_API_KEY'] = self.config['anthropic_api_key']
            logger.info(f"Set ANTHROPIC_API_KEY from config: {self.config['anthropic_api_key'][:20]}...")
        else:
            logger.warning(f"No API key in config. Config keys: {list(self.config.keys())}")
            # Check if it's in environment already
            if os.getenv('ANTHROPIC_API_KEY'):
                logger.info(f"ANTHROPIC_API_KEY found in environment: {os.getenv('ANTHROPIC_API_KEY')[:20]}...")
            else:
                logger.error("ANTHROPIC_API_KEY not found in config or environment!")

        # Register cleanup handler
        atexit.register(self.cleanup)

        logger.info(f"Initialized orchestrator for repository at {self.repo_path}")
        logger.info(f"Workspace directory: {self.workspace_dir.absolute()}")
        logger.info(f"Found {len(self.tasks_config)} feature tasks to process")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from API endpoint or YAML file (fallback).

        Fetches configuration from the Claude-Nine API to avoid Windows encoding issues
        with API keys in YAML files. Falls back to YAML file if API is not available.
        """
        # Try to fetch config from API first
        try:
            api_url = os.getenv('CLAUDE_NINE_API_URL', 'http://localhost:8000')
            response = requests.get(f"{api_url}/api/settings/orchestrator/config", timeout=5)

            if response.status_code == 200:
                config = response.json()
                logger.info(f"Loaded configuration from API endpoint: {api_url}")
                return config
            else:
                logger.warning(f"API returned status {response.status_code}, falling back to file")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch config from API ({e}), falling back to file")

        # Fallback to YAML file
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {
                'main_branch': 'main',
                'check_interval': 60,
                'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', '')
            }
        except Exception as e:
            logger.error(f"Error loading config from file: {e}")
            logger.warning("Using environment variable for API key")
            return {
                'main_branch': 'main',
                'check_interval': 60,
                'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', '')
            }

    def _load_tasks(self, tasks_path: str) -> List[Dict[str, Any]]:
        """Load tasks from YAML file. Returns empty list on error to keep orchestrator alive."""
        try:
            with open(tasks_path, 'r', encoding='utf-8') as f:
                tasks_data = yaml.safe_load(f)

            if 'features' in tasks_data:
                tasks = tasks_data['features']
            else:
                tasks = tasks_data

            logger.info(f"Loaded {len(tasks)} tasks from {tasks_path}")
            return tasks
        except FileNotFoundError:
            logger.error(f"[RESILIENT] Tasks file {tasks_path} not found - orchestrator will wait for tasks")
            # Return empty list instead of crashing - orchestrator stays alive
            return []
        except Exception as e:
            logger.error(f"[RESILIENT] Error loading tasks: {e} - orchestrator will continue with empty task list", exc_info=True)
            # Return empty list instead of crashing - orchestrator stays alive
            return []

    def create_feature_agent(self, feature_config: Dict[str, Any]) -> Tuple[Agent, str]:
        """
        Create a feature developer agent with its own worktree.

        Args:
            feature_config: Configuration for the feature task

        Returns:
            Tuple[Agent, str]: Configured agent and worktree path
        """
        agent_name = feature_config.get('name', 'Feature Developer')
        agent_role = feature_config.get('role', f"{agent_name} Developer")
        agent_goal = feature_config.get('goal', f"Implement {agent_name}")
        branch_name = feature_config.get('branch', f"feature/{agent_name}")

        # Track branch for post-completion merge
        self.feature_branches.append(branch_name)

        # Create isolated worktree for this agent
        worktree_path = self.workspace_dir / f"worktree-{agent_name}"

        logger.info(f"Creating worktree for {agent_name} at {worktree_path}")

        try:
            main_branch = self.config.get('main_branch', 'main')
            worktree_abs_path = self.git_ops.create_worktree(
                branch_name=branch_name,
                worktree_path=str(worktree_path),
                main_branch=main_branch
            )

            # Track for cleanup
            self.worktrees.append(worktree_abs_path)

            # Create git tools pointing to this worktree
            agent_git_tools = create_git_tools(worktree_abs_path)

            backstory = f"""You are an expert software developer working on the {agent_name} feature.
You work in your own isolated workspace at {worktree_abs_path}.
You are on branch '{branch_name}' and your changes will not interfere with other developers.

Your workflow:
1. You already have your own branch checked out in your workspace
2. Implement the feature step by step in your isolated directory
3. Make small, atomic commits for each logical change
4. Write clean, well-documented code

IMPORTANT: You are working in an isolated worktree directory. All file operations
happen in your own workspace: {worktree_abs_path}

Always make commits with descriptive messages. Work independently and focus on your feature.
"""

            # Create LLM with explicit API key
            llm = LLM(
                model="anthropic/claude-sonnet-4-5-20250929",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                max_tokens=4096
            )

            agent = Agent(
                role=agent_role,
                goal=agent_goal,
                backstory=backstory,
                tools=agent_git_tools,
                llm=llm,
                verbose=True,
                allow_delegation=False
            )

            logger.info(f"Created feature agent: {agent_name} with worktree at {worktree_abs_path}")
            return agent, worktree_abs_path

        except Exception as e:
            logger.error(f"[RESILIENT] Failed to create agent for {agent_name}: {e} - skipping this agent", exc_info=True)
            # Don't crash - return None to skip this agent
            return None, None

    def create_feature_task(self, agent: Agent, feature_config: Dict[str, Any], worktree_path: str) -> Task:
        """
        Create a task for a feature agent.

        Args:
            agent: The agent to assign the task to
            feature_config: Configuration for the feature
            worktree_path: Path to the agent's worktree

        Returns:
            Task: Configured CrewAI task
        """
        branch_name = feature_config.get('branch', f"feature/{feature_config['name']}")
        description = feature_config.get('description', '')
        expected_output = feature_config.get('expected_output', 'Feature implemented and committed')

        task_description = f"""
Implement the {feature_config['name']} feature on branch '{branch_name}'.

IMPORTANT: You are working in an isolated worktree at: {worktree_path}
Your branch '{branch_name}' is already checked out. All file operations happen in your worktree.

{description}

Workflow:
1. You are already on branch '{branch_name}' in your isolated workspace
2. Implement the feature following the requirements
3. Make incremental commits as you complete each part
4. Ensure code is well-documented and tested

Your worktree: {worktree_path}
Your branch: {branch_name}
Expected output: {expected_output}

Work independently and don't worry about other developers - you have your own workspace!
"""

        task = Task(
            description=task_description,
            agent=agent,
            expected_output=expected_output,
            async_execution=True  # Parallel execution - all tasks run concurrently
        )

        logger.info(f"Created task for feature: {feature_config['name']} on branch {branch_name}")
        return task

    def create_resolver_agent(self) -> Agent:
        """
        Create a resolver agent for handling merge conflicts.

        The resolver agent understands code and can intelligently resolve
        merge conflicts by analyzing both versions and producing a merged result.

        Returns:
            Agent: Configured resolver agent
        """
        from crewai_tools import tool

        # Create tools for the resolver agent
        @tool("Read Conflict")
        def read_conflict(file_path: str) -> str:
            """
            Read a file with merge conflict markers.
            Returns the full content including conflict markers, plus parsed ours/theirs sections.
            """
            try:
                conflict_info = self.git_ops.get_conflict_content(file_path)
                return f"""File: {file_path}

=== FULL CONTENT WITH CONFLICT MARKERS ===
{conflict_info['full_content']}

=== OUR VERSION (current branch) ===
{conflict_info['ours']}

=== THEIR VERSION (incoming branch) ===
{conflict_info['theirs']}
"""
            except Exception as e:
                return f"Error reading conflict: {e}"

        @tool("Resolve Conflict")
        def resolve_conflict(file_path: str, resolved_content: str) -> str:
            """
            Write the resolved content to a conflicting file and stage it.
            The resolved_content should be the final merged version WITHOUT conflict markers.
            """
            try:
                self.git_ops.resolve_conflict(file_path, resolved_content)
                return f"Successfully resolved and staged: {file_path}"
            except Exception as e:
                return f"Error resolving conflict: {e}"

        @tool("List Conflicts")
        def list_conflicts() -> str:
            """List all files with unresolved merge conflicts."""
            try:
                status = self.git_ops.repo.git.status('--porcelain')
                conflicts = []
                for line in status.split('\n'):
                    if line.startswith('UU ') or line.startswith('AA '):
                        conflicts.append(line[3:].strip())
                if conflicts:
                    return "Conflicting files:\n" + "\n".join(f"  - {f}" for f in conflicts)
                else:
                    return "No conflicts remaining"
            except Exception as e:
                return f"Error listing conflicts: {e}"

        @tool("Complete Merge")
        def complete_merge(commit_message: str) -> str:
            """
            Complete the merge after all conflicts are resolved.
            Call this only after all conflicts have been resolved.
            """
            try:
                success = self.git_ops.complete_merge(commit_message)
                if success:
                    return f"Merge completed successfully with message: {commit_message}"
                else:
                    return "Failed to complete merge - there may be unresolved conflicts"
            except Exception as e:
                return f"Error completing merge: {e}"

        backstory = """You are an expert code merge resolver. Your job is to resolve merge conflicts
intelligently by understanding both versions of the code and producing a clean merged result.

When resolving conflicts:
1. First use 'List Conflicts' to see all conflicting files
2. For each file, use 'Read Conflict' to see both versions
3. Analyze the changes - understand what each version is trying to do
4. Create a merged version that incorporates both changes correctly
5. Use 'Resolve Conflict' to write the resolved content
6. After all files are resolved, use 'Complete Merge' to finish

Guidelines for resolution:
- If both sides add different code, include both (in logical order)
- If both sides modify the same code differently, combine the intent of both
- If one side deletes and another modifies, prefer the modification unless it's clearly obsolete
- Preserve code style and formatting
- Ensure the result is syntactically valid code
"""

        llm = LLM(
            model="anthropic/claude-sonnet-4-5-20250929",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=8192  # Larger for code resolution
        )

        agent = Agent(
            role="Merge Conflict Resolver",
            goal="Resolve all merge conflicts intelligently to produce clean, working code",
            backstory=backstory,
            tools=[read_conflict, resolve_conflict, list_conflicts, complete_merge],
            llm=llm,
            verbose=True,
            allow_delegation=False
        )

        logger.info("Created resolver agent for conflict resolution")
        return agent

    def resolve_conflicts(
        self,
        failed_branch: str,
        conflicting_files: List[str],
        integration_branch: str
    ) -> bool:
        """
        Use the resolver agent to resolve merge conflicts.

        Args:
            failed_branch: The branch that caused the conflict
            conflicting_files: List of files with conflicts
            integration_branch: The integration branch being merged into

        Returns:
            bool: True if conflicts were resolved successfully
        """
        logger.info("="*80)
        logger.info(f"Resolver Agent: Attempting to resolve conflicts from {failed_branch}")
        logger.info(f"Conflicting files: {conflicting_files}")
        logger.info("="*80)

        try:
            # First, restart the merge (it was aborted earlier)
            self.git_ops.repo.heads[integration_branch].checkout()
            merge_result = self.git_ops.start_merge_with_conflicts(failed_branch)

            if not merge_result["has_conflicts"]:
                # No conflicts this time - just complete the merge
                self.git_ops.complete_merge(f"Merge {failed_branch} into {integration_branch}")
                logger.info(f"Merge of {failed_branch} completed without conflicts on retry")
                return True

            # Create resolver agent and task
            resolver = self.create_resolver_agent()

            task_description = f"""Resolve the merge conflicts from merging '{failed_branch}' into '{integration_branch}'.

Conflicting files:
{chr(10).join(f'  - {f}' for f in merge_result['conflicting_files'])}

Steps:
1. Use 'List Conflicts' to confirm the conflicting files
2. For each conflicting file:
   a. Use 'Read Conflict' to see both versions
   b. Analyze what each version is trying to do
   c. Create a merged version that makes sense
   d. Use 'Resolve Conflict' to write your resolution
3. After resolving all files, use 'Complete Merge' with message:
   "Merge {failed_branch} into {integration_branch} (conflicts resolved)"

Be careful to produce valid, working code in your resolutions.
"""

            task = Task(
                description=task_description,
                agent=resolver,
                expected_output="All conflicts resolved and merge completed"
            )

            # Run the resolver
            crew = Crew(
                agents=[resolver],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )

            result = crew.kickoff()
            logger.info(f"Resolver completed: {result}")

            # Verify merge was completed
            try:
                # Check if we're still in a merge state
                self.git_ops.repo.git.status()
                logger.info("Conflicts resolved successfully")
                return True
            except Exception:
                logger.error("Merge may not have completed properly")
                return False

        except Exception as e:
            logger.error(f"Resolver failed: {e}", exc_info=True)
            # Abort any in-progress merge
            self.git_ops.abort_merge()
            return False

    def push_all_branches(self) -> List[str]:
        """
        Push all feature branches to remote after tasks complete.

        Returns:
            List[str]: List of successfully pushed branches
        """
        logger.info("="*80)
        logger.info("Post-completion: Pushing all feature branches to remote")
        logger.info("="*80)

        pushed_branches = []
        for branch_name in self.feature_branches:
            try:
                self.git_ops.push_branch(branch_name)
                pushed_branches.append(branch_name)
                logger.info(f"Successfully pushed branch: {branch_name}")
            except Exception as e:
                logger.error(f"Failed to push branch {branch_name}: {e}")

        return pushed_branches

    def merge_all_branches(self) -> Dict[str, Any]:
        """
        Merge all feature branches into a single integration branch.

        This is the post-completion merge phase. Creates an integration branch
        from main and merges each feature branch sequentially.

        Returns:
            Dict with merge result:
                - success: bool
                - integration_branch: str
                - merged_branches: List[str]
                - failed_branch: str or None
                - conflicting_files: List[str]
        """
        logger.info("="*80)
        logger.info("Post-completion: Merging all feature branches into integration branch")
        logger.info("="*80)

        if not self.feature_branches:
            logger.warning("No feature branches to merge")
            return {
                "success": True,
                "integration_branch": None,
                "merged_branches": [],
                "failed_branch": None,
                "conflicting_files": []
            }

        main_branch = self.config.get('main_branch', 'main')

        result = self.git_ops.merge_branches_into_integration(
            feature_branches=self.feature_branches,
            main_branch=main_branch
        )

        # If merge failed due to conflicts, try to resolve them
        if not result["success"] and result["failed_branch"]:
            logger.info("Attempting automatic conflict resolution...")

            resolved = self.resolve_conflicts(
                failed_branch=result["failed_branch"],
                conflicting_files=result["conflicting_files"],
                integration_branch=result["integration_branch"]
            )

            if resolved:
                # Add the resolved branch to merged list
                result["merged_branches"].append(result["failed_branch"])

                # Continue merging remaining branches
                remaining_branches = [
                    b for b in self.feature_branches
                    if b not in result["merged_branches"]
                ]

                if remaining_branches:
                    logger.info(f"Continuing with remaining branches: {remaining_branches}")
                    for branch in remaining_branches:
                        merge_result = self.git_ops.start_merge_with_conflicts(branch)
                        if merge_result["has_conflicts"]:
                            # Try to resolve this one too
                            if self.resolve_conflicts(branch, merge_result["conflicting_files"], result["integration_branch"]):
                                result["merged_branches"].append(branch)
                            else:
                                result["failed_branch"] = branch
                                result["conflicting_files"] = merge_result["conflicting_files"]
                                break
                        else:
                            self.git_ops.complete_merge(f"Merge {branch} into {result['integration_branch']}")
                            result["merged_branches"].append(branch)

                # Check if all branches were merged
                if set(result["merged_branches"]) == set(self.feature_branches):
                    result["success"] = True
                    result["failed_branch"] = None
                    result["conflicting_files"] = []
                    logger.info("All conflicts resolved successfully!")

        if result["success"]:
            logger.info(f"Successfully merged all branches into {result['integration_branch']}")
            logger.info(f"Merged branches: {result['merged_branches']}")

            # Push the integration branch to remote
            try:
                self.git_ops.push_branch(result["integration_branch"])
                logger.info(f"Pushed integration branch: {result['integration_branch']}")
            except Exception as e:
                logger.error(f"Failed to push integration branch: {e}")
        else:
            logger.error(f"Merge failed at branch: {result['failed_branch']}")
            logger.error(f"Conflicting files: {result['conflicting_files']}")
            logger.error("Could not automatically resolve all conflicts")

        return result

    def create_pull_request(
        self,
        integration_branch: str,
        merged_branches: List[str],
        target_branch: str = "main"
    ) -> Optional[str]:
        """
        Create a pull request from the integration branch to main using gh CLI.

        Args:
            integration_branch: The integration branch to create PR from
            merged_branches: List of feature branches that were merged
            target_branch: Target branch for the PR (default: main)

        Returns:
            str: PR URL if successful, None if failed
        """
        logger.info("="*80)
        logger.info("Post-completion: Creating pull request")
        logger.info("="*80)

        # Build PR title
        if len(merged_branches) == 1:
            title = f"Feature: {merged_branches[0]}"
        else:
            title = f"Integration: {len(merged_branches)} features merged"

        # Build PR body
        body_lines = [
            "## Summary",
            "",
            f"This PR contains {len(merged_branches)} merged feature branch(es):",
            ""
        ]
        for branch in merged_branches:
            body_lines.append(f"- `{branch}`")

        body_lines.extend([
            "",
            "## Merged from integration branch",
            "",
            f"Integration branch: `{integration_branch}`",
            "",
            "---",
            "",
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
        ])

        body = "\n".join(body_lines)

        try:
            # Use gh CLI to create the PR
            result = subprocess.run(
                [
                    "gh", "pr", "create",
                    "--base", target_branch,
                    "--head", integration_branch,
                    "--title", title,
                    "--body", body
                ],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )

            if result.returncode == 0:
                pr_url = result.stdout.strip()
                logger.info(f"Successfully created PR: {pr_url}")
                return pr_url
            else:
                logger.error(f"Failed to create PR: {result.stderr}")
                return None

        except FileNotFoundError:
            logger.error("gh CLI not found. Install it from https://cli.github.com/")
            return None
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return None

    def cleanup(self):
        """Clean up all worktrees on shutdown."""
        # Stop telemetry collector
        shutdown_telemetry()

        if not self.worktrees:
            return

        logger.info("="*80)
        logger.info("Cleaning up worktrees...")
        logger.info("="*80)

        try:
            self.git_ops.cleanup_all_worktrees(str(self.workspace_dir))
            logger.info("All worktrees cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def run(self):
        """
        Run the orchestrator with all agents and tasks.
        """
        try:
            logger.info("="*80)
            logger.info("Starting Multi-Agent Orchestrator with Worktrees")
            logger.info("="*80)

            # Create agents and tasks
            feature_agents = []
            feature_tasks = []
            worktree_paths = []

            # Check if we have tasks to process
            if not self.tasks_config:
                logger.warning("[RESILIENT] No tasks loaded - orchestrator will stay alive but idle")
                logger.info("Waiting for tasks to be added...")
                # Keep orchestrator alive but don't crash
                import time
                while self.running:
                    time.sleep(10)
                    logger.info("[RESILIENT] Still waiting for tasks...")
                return None

            for feature_config in self.tasks_config:
                agent, worktree_path = self.create_feature_agent(feature_config)
                # Skip agents that failed to create
                if agent is None:
                    logger.warning(f"[RESILIENT] Skipping agent for {feature_config.get('name', 'unknown')}")
                    continue
                task = self.create_feature_task(agent, feature_config, worktree_path)
                feature_agents.append(agent)
                feature_tasks.append(task)
                worktree_paths.append(worktree_path)

            # Note: Monitor agent removed - merge will happen in post-completion phase
            # All agents work on their tasks, then we push and merge branches after completion

            logger.info(f"Created {len(feature_agents)} feature agents (each with isolated worktree)")
            logger.info(f"Worktrees created at: {[str(p) for p in worktree_paths]}")
            logger.info(f"Starting crew with {len(feature_tasks)} tasks (parallel execution)")

            # Initialize telemetry if team_id provided
            if self.team_id:
                try:
                    # Extract agent names from feature configs
                    agent_names = [fc.get("name", f"Agent-{idx}") for idx, fc in enumerate(self.tasks_config)]

                    # Initialize telemetry collector using global function
                    api_url = os.getenv("CLAUDE_NINE_API_URL", "http://localhost:8000")
                    collector = initialize_telemetry(
                        team_id=self.team_id,
                        agent_names=agent_names,
                        api_url=api_url,
                        check_interval=2
                    )
                    logger.info(f"Started telemetry collection for team {self.team_id}")

                    # Add initial activity logs for each agent
                    for agent_name in agent_names:
                        collector.add_activity_log(
                            agent_name=agent_name,
                            level="info",
                            message=f"Agent {agent_name} created and initialized",
                            source="orchestrator"
                        )
                except Exception as e:
                    logger.warning(f"Failed to start telemetry: {e}")


            # Create and run crew with parallel execution
            # All tasks run concurrently - each agent works on its task simultaneously
            crew = Crew(
                agents=feature_agents,
                tasks=feature_tasks,
                process=Process.sequential,  # Sequential process, but tasks marked async run in parallel
                verbose=True
            )

            # Run the crew
            logger.info("Starting crew execution...")
            result = crew.kickoff()

            logger.info("="*80)
            logger.info("All feature tasks completed")
            logger.info("="*80)

            # Post-completion Phase 1: Push all branches to remote
            pushed_branches = self.push_all_branches()

            # Post-completion Phase 2: Merge all branches into integration branch
            merge_result = self.merge_all_branches()

            # Post-completion Phase 3: Create PR if merge succeeded
            pr_url = None
            if merge_result["success"] and merge_result["integration_branch"]:
                pr_url = self.create_pull_request(
                    integration_branch=merge_result["integration_branch"],
                    merged_branches=merge_result["merged_branches"],
                    target_branch=self.config.get('main_branch', 'main')
                )

            logger.info("="*80)
            logger.info("Orchestrator completed successfully")
            logger.info(f"Pushed {len(pushed_branches)} branches: {pushed_branches}")
            if merge_result["success"]:
                logger.info(f"Integration branch: {merge_result['integration_branch']}")
                logger.info(f"All {len(merge_result['merged_branches'])} branches merged successfully")
                if pr_url:
                    logger.info(f"Pull request created: {pr_url}")
            else:
                logger.warning(f"Merge failed at: {merge_result['failed_branch']}")
                logger.warning(f"Conflicts in: {merge_result['conflicting_files']}")
            logger.info("="*80)
            logger.info(f"Result: {result}")

            return result

        except KeyboardInterrupt:
            logger.info("\n" + "="*80)
            logger.info("Received interrupt signal, shutting down gracefully...")
            logger.info("="*80)
            self.running = False
            self.cleanup()
            return None

        except Exception as e:
            logger.error(f"Error during orchestration: {e}", exc_info=True)
            raise

        finally:
            # Cleanup happens via atexit, but call it explicitly too
            self.cleanup()

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"\nReceived signal {signum}")
            self.running = False
            self.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for the orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-Agent Orchestrator for parallel feature development with git worktrees"
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--tasks',
        default='tasks/example_tasks.yaml',
        help='Path to tasks file (default: tasks/example_tasks.yaml)'
    )
    parser.add_argument(
        '--repo',
        default='.',
        help='Path to repository (default: current directory)'
    )
    parser.add_argument(
        '--cleanup-only',
        action='store_true',
        help='Only clean up existing worktrees and exit'
    )
    parser.add_argument(
        '--team-id',
        default=None,
        help='Team ID for API integration (optional)'
    )

    args = parser.parse_args()

    # Change to repo directory if specified
    if args.repo != '.':
        os.chdir(args.repo)
        logger.info(f"Changed directory to {args.repo}")

    # Verify we're in a git repository
    if not os.path.exists('.git'):
        logger.error("Not in a git repository! Please run from a git repository root.")
        sys.exit(1)

    # Create workspace directory
    workspace = Path(".agent-workspace")
    workspace.mkdir(exist_ok=True)
    logger.info(f"Using workspace directory: {workspace.absolute()}")

    # If cleanup-only mode, just clean up and exit
    if args.cleanup_only:
        logger.info("Cleanup-only mode: removing all worktrees")
        try:
            git_ops = GitOperations(".")
            git_ops.cleanup_all_worktrees(str(workspace))
            logger.info("Cleanup complete")
            return 0
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 1

    # Create and run orchestrator
    orchestrator = MultiAgentOrchestrator(
        config_path=args.config,
        tasks_path=args.tasks,
        team_id=args.team_id
    )
    orchestrator.setup_signal_handlers()

    try:
        result = orchestrator.run()
        logger.info("Orchestrator finished successfully")
        return 0
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
