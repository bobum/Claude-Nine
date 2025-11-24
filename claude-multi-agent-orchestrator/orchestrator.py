#!/usr/bin/env python3
"""
Multi-Agent Orchestrator for CrewAI with Claude.

This orchestrator manages multiple Claude agents working simultaneously
on different features in a monorepo, with intelligent merge conflict resolution.

Uses git worktrees to give each agent an isolated working directory,
enabling true parallel development without interference.
"""

import os
import sys
import time
import yaml
import logging
import signal
import atexit
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from crewai import Agent, Task, Crew, Process
from git_tools import create_git_tools
from git_operations import GitOperations


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
    - Continuous conflict monitoring
    - Intelligent merge conflict resolution
    - Automatic merge when ready
    - Automatic cleanup of worktrees on shutdown
    """

    def __init__(self, config_path: str = "config.yaml", tasks_path: str = "tasks/example_tasks.yaml"):
        """
        Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
            tasks_path: Path to tasks definition file
        """
        self.config = self._load_config(config_path)
        self.tasks_config = self._load_tasks(tasks_path)
        self.repo_path = os.getcwd()

        # Main git operations (for monitor and coordination)
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
        self.running = True

        # Set up API key
        if 'anthropic_api_key' in self.config and self.config['anthropic_api_key']:
            os.environ['ANTHROPIC_API_KEY'] = self.config['anthropic_api_key']

        # Register cleanup handler
        atexit.register(self.cleanup)

        logger.info(f"Initialized orchestrator for repository at {self.repo_path}")
        logger.info(f"Workspace directory: {self.workspace_dir.absolute()}")
        logger.info(f"Found {len(self.tasks_config)} feature tasks to process")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
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
            logger.error(f"Error loading config: {e}")
            raise

    def _load_tasks(self, tasks_path: str) -> List[Dict[str, Any]]:
        """Load tasks from YAML file."""
        try:
            with open(tasks_path, 'r') as f:
                tasks_data = yaml.safe_load(f)

            if 'features' in tasks_data:
                tasks = tasks_data['features']
            else:
                tasks = tasks_data

            logger.info(f"Loaded {len(tasks)} tasks from {tasks_path}")
            return tasks
        except FileNotFoundError:
            logger.error(f"Tasks file {tasks_path} not found")
            raise
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            raise

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
4. Push your branch regularly so the monitor can track progress
5. Write clean, well-documented code

IMPORTANT: You are working in an isolated worktree directory. All file operations
happen in your own workspace: {worktree_abs_path}

Always make commits with descriptive messages. Work independently and focus on your feature.
"""

            agent = Agent(
                role=agent_role,
                goal=agent_goal,
                backstory=backstory,
                tools=agent_git_tools,
                llm="claude-sonnet-4-20250514",
                verbose=True,
                allow_delegation=False
            )

            logger.info(f"Created feature agent: {agent_name} with worktree at {worktree_abs_path}")
            return agent, worktree_abs_path

        except Exception as e:
            logger.error(f"Failed to create agent for {agent_name}: {e}")
            raise

    def create_monitor_agent(self) -> Agent:
        """
        Create the monitor agent for conflict resolution.

        The monitor agent works in the main repository directory
        to oversee all branches.

        Returns:
            Agent: Configured monitor agent
        """
        monitor_role = "Merge Conflict Monitor and Resolver"
        monitor_goal = """Monitor all feature branches for potential merge conflicts and resolve them intelligently.
Ensure all features can be merged into main without conflicts."""

        # Monitor uses main repo tools (not a worktree)
        monitor_tools = create_git_tools(self.repo_path)

        backstory = f"""You are an expert at managing parallel development and resolving merge conflicts.
You work in the main repository at {self.repo_path}.

Your responsibilities:

1. Continuously monitor all feature branches (they're being developed in separate worktrees)
2. Check for commits that could cause merge conflicts
3. When conflicts are detected:
   - Read both versions of the conflicting files
   - Understand the intent of each change
   - Determine if changes are compatible or need refactoring
   - Either auto-resolve compatible changes or flag for developer review
4. Merge branches that are ready and conflict-free
5. Maintain the integrity of the main branch

You have deep knowledge of code architecture and can make intelligent decisions
about conflict resolution. You prioritize:
- Code correctness over convenience
- Clear communication about conflicts
- Safe, atomic merges

Use your git tools to check conflicts, read files from different branches,
and perform merges when appropriate.

NOTE: Feature agents are working in isolated worktrees, but you see all their
branches in the shared repository. You don't need to worry about their working
directories - just monitor and merge their branches.
"""

        agent = Agent(
            role=monitor_role,
            goal=monitor_goal,
            backstory=backstory,
            tools=monitor_tools,
            llm="claude-sonnet-4-20250514",
            verbose=True,
            allow_delegation=False
        )

        logger.info("Created monitor agent for conflict resolution")
        return agent

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
4. Push your branch after each commit so the monitor can see your progress
5. Ensure code is well-documented and tested

Your worktree: {worktree_path}
Your branch: {branch_name}
Expected output: {expected_output}

Work independently and don't worry about other developers - you have your own workspace!
"""

        task = Task(
            description=task_description,
            agent=agent,
            expected_output=expected_output,
            async_execution=True  # Enable parallel execution
        )

        logger.info(f"Created task for feature: {feature_config['name']} on branch {branch_name}")
        return task

    def create_monitor_task(self, agent: Agent) -> Task:
        """
        Create the monitoring task for conflict detection and resolution.

        Args:
            agent: The monitor agent

        Returns:
            Task: Configured monitoring task
        """
        check_interval = self.config.get('check_interval', 60)
        main_branch = self.config.get('main_branch', 'main')

        task_description = f"""
Continuously monitor all feature branches for merge conflicts and resolve them.

Your monitoring workflow:

1. Every {check_interval} seconds, check all branches
2. For each feature branch (they're being developed in separate worktrees):
   - Check if it has new commits
   - Test for merge conflicts with {main_branch}
   - If conflicts found:
     a. Read conflicting files from both branches
     b. Analyze the changes and their intent
     c. Determine if changes are compatible
     d. If compatible: document resolution strategy
     e. If incompatible: flag for manual review with detailed explanation
3. For branches without conflicts:
   - Verify the feature appears complete (has commits with implementation)
   - Merge into {main_branch} when ready
   - Log the successful merge

Use your tools to:
- Get all branches
- Check for conflicts
- Read files from different branches
- Merge when appropriate

Continue monitoring until all features are merged or you receive a stop signal.
Report status regularly.

NOTE: Feature developers are working in isolated worktrees. You're monitoring
their branches in the shared repository. Focus on branch management and merging.
"""

        task = Task(
            description=task_description,
            agent=agent,
            expected_output="All features monitored and conflicts resolved",
            async_execution=True
        )

        logger.info("Created monitoring task")
        return task

    def cleanup(self):
        """Clean up all worktrees on shutdown."""
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

            for feature_config in self.tasks_config:
                agent, worktree_path = self.create_feature_agent(feature_config)
                task = self.create_feature_task(agent, feature_config, worktree_path)
                feature_agents.append(agent)
                feature_tasks.append(task)
                worktree_paths.append(worktree_path)

            # Create monitor agent and task
            monitor_agent = self.create_monitor_agent()
            monitor_task = self.create_monitor_task(monitor_agent)

            # Combine all agents and tasks
            all_agents = feature_agents + [monitor_agent]
            all_tasks = feature_tasks + [monitor_task]

            logger.info(f"Created {len(feature_agents)} feature agents (each with isolated worktree)")
            logger.info(f"Created 1 monitor agent (working in main repo)")
            logger.info(f"Worktrees created at: {[str(p) for p in worktree_paths]}")
            logger.info(f"Starting crew with {len(all_tasks)} tasks in parallel")

            # Create and run crew
            crew = Crew(
                agents=all_agents,
                tasks=all_tasks,
                process=Process.parallel,  # Run tasks in parallel
                verbose=True
            )

            # Run the crew
            logger.info("Starting crew execution...")
            result = crew.kickoff()

            logger.info("="*80)
            logger.info("Orchestrator completed successfully")
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
        tasks_path=args.tasks
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
