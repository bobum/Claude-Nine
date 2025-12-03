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
import uuid
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


class MockLLM:
    """
    Mock LLM for dry-run mode.
    
    Simulates LLM responses without making actual API calls.
    Useful for testing the orchestrator workflow without consuming credits.
    
    Enhanced for realistic UI testing:
    - Simulates realistic delays (5-10 seconds per "LLM call")
    - Generates fake telemetry (CPU, memory, token usage)
    - Updates task status via API
    """
    
    # Class-level tracking for all mock instances
    _instances: Dict[str, 'MockLLM'] = {}
    
    def __init__(self, model: str = "mock", api_key: str = None, max_tokens: int = 4096, 
                 agent_name: str = None, work_item_id: str = None, team_id: str = None, **kwargs):
        self.model = model
        self.max_tokens = max_tokens
        self._call_count = 0
        self.agent_name = agent_name
        self.work_item_id = work_item_id
        self.team_id = team_id
        self.api_url = os.getenv("CLAUDE_NINE_API_URL", "http://localhost:8000")
        
        # Token tracking for this agent
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        
        # Register this instance
        if agent_name:
            MockLLM._instances[agent_name] = self
        
        logger.info(f"MockLLM initialized (model={model}, agent={agent_name}, work_item={work_item_id})")
    
    def _update_task_status(self, status: str):
        """Update task status via API."""
        if not self.work_item_id:
            return
        try:
            response = requests.patch(
                f"{self.api_url}/api/runs/tasks/by-work-item/{self.work_item_id}",
                params={
                    "status": status,
                    "agent_name": self.agent_name
                },
                timeout=5
            )
            if response.status_code == 200:
                logger.info(f"[DRY-RUN] Updated task status to '{status}' for work_item {self.work_item_id}")
            else:
                logger.warning(f"[DRY-RUN] Failed to update task status: {response.status_code}")
        except Exception as e:
            logger.warning(f"[DRY-RUN] Could not update task status: {e}")
    
    def _send_telemetry(self):
        """Send fake telemetry data to the API."""
        if not self.agent_name or not self.team_id:
            return
        
        import random
        
        # Generate realistic-looking metrics
        cpu_percent = random.uniform(15.0, 45.0)
        memory_mb = random.uniform(200.0, 500.0)
        
        telemetry_data = {
            "team_id": self.team_id,
            "agent_name": self.agent_name,
            "process_metrics": {
                "pid": os.getpid(),
                "cpu_percent": round(cpu_percent, 1),
                "memory_mb": round(memory_mb, 1),
                "threads": 4,
                "status": "running"
            },
            "token_usage": {
                "model": "claude-sonnet-4-5",
                "input_tokens": self._total_input_tokens,
                "output_tokens": self._total_output_tokens,
                "total_tokens": self._total_input_tokens + self._total_output_tokens
            },
            "git_activities": [],
            "activity_logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "message": f"Processing task (call #{self._call_count})",
                    "source": "mock_llm",
                    "agent_name": self.agent_name
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/telemetry/agent/{self.agent_name}",
                json=telemetry_data,
                timeout=5
            )
            if response.status_code == 200:
                logger.debug(f"[DRY-RUN] Sent telemetry for {self.agent_name}")
            else:
                logger.warning(f"[DRY-RUN] Failed to send telemetry: {response.status_code}")
        except Exception as e:
            logger.warning(f"[DRY-RUN] Could not send telemetry: {e}")
    
    def call(self, messages, **kwargs):
        """Simulate LLM call with realistic delays and telemetry."""
        import random
        
        self._call_count += 1
        
        # Extract the last user message to understand context
        last_message = ""
        if messages:
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    last_message = msg.get("content", "")[:200]
                    break
        
        logger.info(f"[DRY-RUN] MockLLM call #{self._call_count} for {self.agent_name}: {last_message[:50]}...")
        
        # First call: transition to "running" status with 1-3s pending delay
        if self._call_count == 1:
            pending_delay = random.uniform(1.0, 3.0)
            logger.info(f"[DRY-RUN] Simulating pending state for {pending_delay:.1f}s")
            time.sleep(pending_delay)
            self._update_task_status("running")
        
        # Simulate work with 5-10 second delay, sending telemetry periodically
        work_duration = random.uniform(5.0, 10.0)
        logger.info(f"[DRY-RUN] Simulating work for {work_duration:.1f}s")
        
        elapsed = 0.0
        telemetry_interval = 2.0  # Send telemetry every 2 seconds
        
        while elapsed < work_duration:
            sleep_time = min(telemetry_interval, work_duration - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time
            
            # Simulate token accumulation
            self._total_input_tokens += random.randint(500, 1500)
            self._total_output_tokens += random.randint(200, 800)
            
            # Send telemetry update
            self._send_telemetry()
        
        logger.info(f"[DRY-RUN] MockLLM call #{self._call_count} completed")
        
        # Return a generic task completion response
        return f"""I have analyzed the task and here is my simulated response (dry-run mode, call #{self._call_count}).

For this feature implementation task, I would:
1. Create the necessary files and directories
2. Implement the core functionality
3. Add appropriate error handling
4. Write tests for the new code
5. Commit the changes with a descriptive message

[DRY-RUN] This is a simulated response. No actual code changes were made.
[DRY-RUN] Tokens used: {self._total_input_tokens} input, {self._total_output_tokens} output

Final Answer: Task completed successfully (simulated in dry-run mode).
"""
    
    def __call__(self, messages, **kwargs):
        """Allow the mock to be called directly."""
        return self.call(messages, **kwargs)




class MultiAgentOrchestrator:
    """
    Orchestrates multiple Claude agents working on different features in parallel.

    Features:
    - Parallel feature development on separate branches using git worktrees
    - Each agent gets its own isolated working directory
    - Post-completion merge phase for combining branches
    - Automatic cleanup of worktrees on shutdown
    """

    def __init__(self, config_path: str = "config.yaml", tasks_path: str = "tasks/example_tasks.yaml", team_id: str = None, headless_mode: bool = False, dry_run: bool = False):
        """
        Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
            tasks_path: Path to tasks definition file
            team_id: Team ID for API integration (optional)
            headless_mode: If True, write telemetry to files instead of API
            dry_run: If True, use mock LLM responses instead of real API calls
        """
        self.dry_run = dry_run
        if dry_run:
            logger.info("DRY RUN MODE: Using mock LLM responses (no API credits consumed)")
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

        # Session ID for unique branch naming (8-char GUID)
        self.session_id = str(uuid.uuid4()).replace('-', '')[:8]
        self.integration_branch = f"integration/{self.session_id}"
        logger.info(f"Session ID: {self.session_id}")

        # Telemetry
        self.team_id = team_id
        self.headless_mode = headless_mode
        if headless_mode:
            logger.info("Running in headless mode - telemetry will be written to files")

        # Set up API key - only needed for real mode
        if not self.dry_run:
            env_api_key = os.getenv('ANTHROPIC_API_KEY')
            config_api_key = self.config.get('anthropic_api_key', '')

            if env_api_key and env_api_key.startswith('sk-'):
                logger.info(f"Using ANTHROPIC_API_KEY from environment: {env_api_key[:20]}...")
            elif config_api_key and config_api_key.startswith('sk-'):
                os.environ['ANTHROPIC_API_KEY'] = config_api_key
                logger.info(f"Set ANTHROPIC_API_KEY from config: {config_api_key[:20]}...")
            elif env_api_key:
                logger.warning(f"ANTHROPIC_API_KEY in env doesn't look valid: {env_api_key[:20]}...")
            else:
                logger.error("ANTHROPIC_API_KEY not found in environment or config!")
        else:
            logger.info("DRY RUN MODE: Skipping API key setup - will use mock execution")

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
        # Debug logging - goes to orchestrator.log
        logger.info(f"[_load_tasks] Loading tasks from: {tasks_path}")
        logger.info(f"[_load_tasks] File exists: {os.path.exists(tasks_path)}")

        try:
            with open(tasks_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            logger.info(f"[_load_tasks] File content length: {len(raw_content)} chars")
            logger.info(f"[_load_tasks] First 500 chars: {raw_content[:500]}")

            tasks_data = yaml.safe_load(raw_content)
            logger.info(f"[_load_tasks] Parsed YAML type: {type(tasks_data)}")
            if tasks_data:
                logger.info(f"[_load_tasks] Parsed YAML keys: {list(tasks_data.keys()) if isinstance(tasks_data, dict) else 'not a dict'}")

            if tasks_data and isinstance(tasks_data, dict) and 'features' in tasks_data:
                tasks = tasks_data['features']
                logger.info(f"[_load_tasks] Found 'features' key with {len(tasks) if tasks else 0} items")
            else:
                tasks = tasks_data if tasks_data else []
                logger.info(f"[_load_tasks] No 'features' key, using raw data: {type(tasks)}")

            logger.info(f"[_load_tasks] Returning {len(tasks) if isinstance(tasks, list) else 0} tasks")
            return tasks if isinstance(tasks, list) else []
        except FileNotFoundError:
            logger.error(f"[RESILIENT] Tasks file {tasks_path} not found - orchestrator will wait for tasks")
            return []
        except Exception as e:
            logger.error(f"[RESILIENT] Error loading tasks: {e} - orchestrator will continue with empty task list", exc_info=True)
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
        # Append session ID to branch name for uniqueness
        base_branch = feature_config.get('branch', f"feature/{agent_name}")
        branch_name = f"{base_branch}-{self.session_id}"

        # Track branch for post-completion merge
        self.feature_branches.append(branch_name)

        # Create isolated worktree for this agent (include session ID for uniqueness)
        worktree_path = self.workspace_dir / f"worktree-{agent_name}-{self.session_id}"

        logger.info(f"Creating worktree for {agent_name} at {worktree_path}")

        try:
            # Feature branches are created from integration branch, not main
            worktree_abs_path = self.git_ops.create_worktree(
                branch_name=branch_name,
                worktree_path=str(worktree_path),
                main_branch=self.integration_branch  # Branch from integration
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

            # Create LLM - real or mock based on dry_run flag
            if self.dry_run:
                llm = MockLLM(
                    model="anthropic/claude-sonnet-4-5-20250929",
                    max_tokens=4096,
                    agent_name=agent_name,
                    work_item_id=feature_config.get('work_item_id'),
                    team_id=self.team_id
                )
            else:
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
        # Include session ID in branch name for consistency with create_feature_agent
        base_branch = feature_config.get('branch', f"feature/{feature_config['name']}")
        branch_name = f"{base_branch}-{self.session_id}"
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
        from crewai.tools import tool

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

        # Create LLM - real or mock based on dry_run flag
        if self.dry_run:
            llm = MockLLM(
                model="anthropic/claude-sonnet-4-5-20250929",
                max_tokens=8192,
                agent_name="resolver",
                team_id=self.team_id
            )
        else:
            llm = LLM(
                model="anthropic/claude-sonnet-4-5-20250929",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                max_tokens=8192
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
            # Check if merge is already in progress (MERGE_HEAD exists)
            merge_head_path = os.path.join(self.git_ops.repo.git_dir, 'MERGE_HEAD')
            if os.path.exists(merge_head_path):
                # Merge already in progress - use the conflicting_files passed in
                logger.info("Merge already in progress, using provided conflicting files")
                merge_result = {"has_conflicts": True, "conflicting_files": conflicting_files}
            else:
                # No merge in progress - checkout and start fresh
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

            # Verify merge was completed - check if MERGE_HEAD still exists
            try:
                merge_head_path = os.path.join(self.git_ops.repo.git_dir, 'MERGE_HEAD')
                if os.path.exists(merge_head_path):
                    # Agent didn't complete the merge, do it ourselves
                    logger.warning("Agent didn't complete merge, completing manually...")
                    commit_msg = f"Merge {failed_branch} into {integration_branch} (conflicts resolved)"
                    success = self.git_ops.complete_merge(commit_msg)
                    if not success:
                        logger.error("Failed to complete merge manually")
                        return False
                logger.info("Conflicts resolved successfully")
                return True
            except Exception as e:
                logger.error(f"Merge may not have completed properly: {e}")
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

        # Use the pre-created integration branch with session ID
        result = self.git_ops.merge_branches_into_integration(
            feature_branches=self.feature_branches,
            main_branch=main_branch,
            integration_branch=self.integration_branch  # Use session-based integration branch
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

            # Phase 1: Create integration branch from main and push to remote
            main_branch = self.config.get('main_branch', 'main')
            logger.info(f"Creating integration branch {self.integration_branch} from {main_branch}")
            self.git_ops.create_branch_from_main(self.integration_branch, main_branch)
            self.git_ops.push_branch(self.integration_branch)
            logger.info(f"Pushed integration branch {self.integration_branch} to remote")

            # Phase 2: Create feature branches from integration branch
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
                    telemetry_output_dir = self.workspace_dir / "telemetry"
                    collector = initialize_telemetry(
                        team_id=self.team_id,
                        agent_names=agent_names,
                        api_url=api_url,
                        check_interval=2,
                        output_dir=telemetry_output_dir,
                        headless_mode=self.headless_mode
                    )
                    logger.info(f"Started telemetry collection for team {self.team_id}")
                    if self.headless_mode:
                        logger.info(f"Telemetry output: {telemetry_output_dir}")

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


            # Create and run multiple crews in parallel (one per agent/task)
            # This is the recommended pattern for true parallel execution in CrewAI
            logger.info("Creating individual crews for parallel execution...")

            crews = []
            for agent, task in zip(feature_agents, feature_tasks):
                crew = Crew(
                    agents=[agent],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=True
                )
                crews.append(crew)

            logger.info(f"Created {len(crews)} crews for parallel execution")

            # Run all crews in parallel using asyncio
            import asyncio
            import random

            if self.dry_run:
                # DRY RUN MODE: Fake the crew execution
                logger.info("*** DRY RUN MODE: Faking crew execution ***")
                
                async def mock_crew_execution(crew_index, feature_config):
                    """Simulate crew execution with delays and fake telemetry."""
                    agent_name = feature_config.get('name', f'agent_{crew_index}')
                    work_item_id = feature_config.get('work_item_id')
                    task_description = feature_config.get('description', f'Implement {agent_name}')
                    
                    # Simulate pending -> running transition (1-3 seconds)
                    pending_delay = random.uniform(1.0, 3.0)
                    logger.info(f"[MOCK] {agent_name}: pending for {pending_delay:.1f}s")
                    await asyncio.sleep(pending_delay)
                    
                    # Update task status to running
                    if work_item_id and self.team_id:
                        try:
                            api_url = os.getenv("CLAUDE_NINE_API_URL", "http://localhost:8000")
                            requests.patch(
                                f"{api_url}/api/runs/tasks/by-work-item/{work_item_id}",
                                params={"status": "running", "agent_name": agent_name},
                                timeout=5
                            )
                            logger.info(f"[MOCK] {agent_name}: status -> running")
                        except Exception as e:
                            logger.warning(f"[MOCK] Failed to update task status: {e}")
                    
                    # Simulate work (5-15 seconds) with telemetry updates
                    work_duration = random.uniform(5.0, 15.0)
                    logger.info(f"[MOCK] {agent_name}: working for {work_duration:.1f}s")
                    
                    elapsed = 0.0
                    total_input_tokens = 0
                    total_output_tokens = 0
                    files_read = []
                    files_written = []
                    tool_calls = []
                    git_activities = []
                    activity_logs = []
                    
                    # Simulated actions to cycle through
                    simulated_actions = [
                        ("Analyzing codebase...", None),
                        ("Reading file: src/index.ts", "git_read_file"),
                        ("Calling claude-sonnet-4-5...", None),
                        ("Generating response...", None),
                        ("Writing file: src/feature.ts", "git_write_file"),
                        ("Running tests...", "run_tests"),
                        ("Committing changes...", "git_commit"),
                    ]
                    action_index = 0
                    
                    while elapsed < work_duration:
                        await asyncio.sleep(2.0)
                        elapsed += 2.0
                        
                        # Accumulate fake tokens
                        new_input = random.randint(500, 1500)
                        new_output = random.randint(200, 800)
                        total_input_tokens += new_input
                        total_output_tokens += new_output
                        
                        # Simulate streaming tokens (some iterations show active streaming)
                        is_streaming = random.choice([True, True, False])
                        streaming_tokens = random.randint(50, 200) if is_streaming else None
                        
                        # Cycle through simulated actions
                        current_action, tool_in_progress = simulated_actions[action_index % len(simulated_actions)]
                        action_index += 1
                        
                        # Simulate file operations
                        if "Reading" in current_action:
                            fake_file = f"src/file_{random.randint(1,5)}.ts"
                            if fake_file not in files_read:
                                files_read.append(fake_file)
                        elif "Writing" in current_action:
                            fake_file = f"src/output_{random.randint(1,3)}.ts"
                            if fake_file not in files_written:
                                files_written.append(fake_file)
                        
                        # Simulate tool calls
                        if tool_in_progress:
                            tool_calls.append({
                                "timestamp": datetime.now().isoformat(),
                                "tool": tool_in_progress,
                                "arguments": {"path": f"src/file_{random.randint(1,5)}.ts"},
                                "result": "Success"
                            })
                            # Keep only last 10
                            tool_calls = tool_calls[-10:]
                        
                        # Add activity log
                        activity_logs.append({
                            "timestamp": datetime.now().isoformat(),
                            "level": "info",
                            "message": f"LLM call completed: +{new_input + new_output} tokens (total: {total_input_tokens + total_output_tokens})",
                            "source": "llm",
                            "agent_name": agent_name
                        })
                        activity_logs.append({
                            "timestamp": datetime.now().isoformat(),
                            "level": "info",
                            "message": current_action,
                            "source": "orchestrator",
                            "agent_name": agent_name
                        })
                        # Keep only last 50
                        activity_logs = activity_logs[-50:]
                        
                        # Simulate git activity occasionally
                        if random.random() < 0.2 and elapsed > 3:
                            git_activities.append({
                                "operation": random.choice(["commit", "branch_create"]),
                                "branch": f"feature/{agent_name.lower().replace(' ', '-')}",
                                "message": f"WIP: {task_description[:30]}...",
                                "files_changed": random.randint(1, 5),
                                "timestamp": datetime.now().isoformat(),
                                "agent_name": agent_name
                            })
                            # Keep only last 10
                            git_activities = git_activities[-10:]
                        
                        # Send fake telemetry with all enhanced fields
                        if self.team_id:
                            try:
                                api_url = os.getenv("CLAUDE_NINE_API_URL", "http://localhost:8000")
                                telemetry_data = {
                                    "team_id": self.team_id,
                                    "agent_name": agent_name,
                                    "status": "working",
                                    "current_task": task_description[:100],
                                    "current_action": current_action,
                                    "process_metrics": {
                                        "pid": os.getpid(),
                                        "cpu_percent": round(random.uniform(15.0, 45.0), 1),
                                        "memory_mb": round(random.uniform(200.0, 500.0), 1),
                                        "threads": 4,
                                        "status": "running"
                                    },
                                    "token_usage": {
                                        "model": "claude-sonnet-4-5",
                                        "input_tokens": total_input_tokens,
                                        "output_tokens": total_output_tokens,
                                        "total_tokens": total_input_tokens + total_output_tokens,
                                        "streaming_tokens": streaming_tokens,
                                        "total_tokens_with_streaming": (total_input_tokens + total_output_tokens + streaming_tokens) if streaming_tokens else None
                                    },
                                    "files_read": files_read[-10:],
                                    "files_written": files_written[-10:],
                                    "tool_calls": tool_calls[-10:],
                                    "tool_in_progress": tool_in_progress,
                                    "git_activities": git_activities,
                                    "activity_logs": activity_logs,
                                    "timestamp": datetime.now().isoformat(),
                                    "heartbeat": True,
                                    "event_bus_connected": True  # Simulate as if event bus is connected
                                }
                                requests.post(
                                    f"{api_url}/api/telemetry/agent/{agent_name}",
                                    json=telemetry_data,
                                    timeout=5
                                )
                            except Exception as e:
                                logger.warning(f"[MOCK] Failed to send telemetry: {e}")
                    
                    # Send final "completed" telemetry
                    if self.team_id:
                        try:
                            api_url = os.getenv("CLAUDE_NINE_API_URL", "http://localhost:8000")
                            telemetry_data = {
                                "team_id": self.team_id,
                                "agent_name": agent_name,
                                "status": "completed",
                                "current_task": task_description[:100],
                                "current_action": "Task completed successfully",
                                "process_metrics": {
                                    "pid": os.getpid(),
                                    "cpu_percent": 2.0,
                                    "memory_mb": round(random.uniform(150.0, 200.0), 1),
                                    "threads": 4,
                                    "status": "running"
                                },
                                "token_usage": {
                                    "model": "claude-sonnet-4-5",
                                    "input_tokens": total_input_tokens,
                                    "output_tokens": total_output_tokens,
                                    "total_tokens": total_input_tokens + total_output_tokens,
                                    "streaming_tokens": None,
                                    "total_tokens_with_streaming": None
                                },
                                "files_read": files_read[-10:],
                                "files_written": files_written[-10:],
                                "tool_calls": tool_calls[-10:],
                                "tool_in_progress": None,
                                "git_activities": git_activities,
                                "activity_logs": activity_logs,
                                "timestamp": datetime.now().isoformat(),
                                "heartbeat": True,
                                "event_bus_connected": True
                            }
                            requests.post(
                                f"{api_url}/api/telemetry/agent/{agent_name}",
                                json=telemetry_data,
                                timeout=5
                            )
                        except Exception as e:
                            logger.warning(f"[MOCK] Failed to send final telemetry: {e}")
                    
                    logger.info(f"[MOCK] {agent_name}: completed")
                    return f"Mock result for {agent_name}"

                async def run_mock_parallel():
                    """Run all mock crews in parallel."""
                    tasks = [mock_crew_execution(i, self.tasks_config[i]) for i in range(len(crews))]
                    return await asyncio.gather(*tasks, return_exceptions=True)

                # Execute mock crews
                logger.info("Starting mock parallel execution...")
                try:
                    try:
                        loop = asyncio.get_running_loop()
                        import concurrent.futures
                        future = asyncio.run_coroutine_threadsafe(run_mock_parallel(), loop)
                        results = future.result()
                    except RuntimeError:
                        results = asyncio.run(run_mock_parallel())

                    for idx, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Mock crew {idx} failed: {result}")
                        else:
                            logger.info(f"Mock crew {idx} completed: {result}")

                except Exception as e:
                    logger.error(f"Error during mock execution: {e}")
                    raise

            else:
                # REAL MODE: Execute crews with CrewAI
                async def run_crews_parallel(crews_list):
                    """Run all crews in parallel and collect results."""
                    tasks = [crew.kickoff_async() for crew in crews_list]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    return results

                logger.info("Starting parallel crew execution...")
                try:
                    try:
                        loop = asyncio.get_running_loop()
                        import concurrent.futures
                        future = asyncio.run_coroutine_threadsafe(run_crews_parallel(crews), loop)
                        results = future.result()
                    except RuntimeError:
                        results = asyncio.run(run_crews_parallel(crews))

                    for idx, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Crew {idx} failed with error: {result}")
                        else:
                            logger.info(f"Crew {idx} completed successfully")

                except Exception as e:
                    logger.error(f"Error during parallel crew execution: {e}")
                    raise

            logger.info("="*80)
            logger.info("All feature tasks completed")
            logger.info("="*80)

            # Post-completion Phase 1: Push all branches to remote
            pushed_branches = self.push_all_branches()

            # Post-completion Phase 2: Merge all branches into integration branch
            merge_result = self.merge_all_branches()

            # Post-completion Phase 3: Create PR if merge succeeded and configured
            pr_url = None
            create_pr = self.config.get('create_pr', False)  # Default: off (platform-specific)
            if create_pr and merge_result["success"] and merge_result["integration_branch"]:
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
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Headless mode: write telemetry to files instead of API'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode: use mock LLM responses instead of real API calls (saves credits)'
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

    # Pre-run check: detect existing worktrees in workspace
    try:
        git_ops = GitOperations(".")
        all_worktrees = git_ops.list_worktrees()
        # Filter for worktrees in our workspace directory (exclude main repo)
        workspace_abs = str(workspace.absolute())
        existing_worktrees = [w for w in all_worktrees if workspace_abs in w.get('path', '')]

        if existing_worktrees:
            logger.warning(f"Found {len(existing_worktrees)} existing worktree(s) in workspace")
            if args.headless:
                logger.info("Headless mode: auto-cleaning existing worktrees")
                git_ops.cleanup_all_worktrees(str(workspace))
            else:
                print(f"\n⚠️  Existing worktrees detected ({len(existing_worktrees)} found):")
                for wt in existing_worktrees:
                    print(f"   - {wt.get('path', 'unknown')} ({wt.get('branch', 'no branch')})")
                response = input("\nClean up before starting? [y/N]: ").strip().lower()
                if response == 'y':
                    logger.info("User requested cleanup")
                    git_ops.cleanup_all_worktrees(str(workspace))
                    logger.info("Cleanup complete")
                else:
                    logger.error("Cannot start with existing worktrees. Run with --cleanup-only first.")
                    return 1
    except Exception as e:
        logger.warning(f"Pre-run worktree check failed: {e}")
        # Continue anyway - this is a safety check, not critical

    # Create and run orchestrator
    orchestrator = MultiAgentOrchestrator(
        config_path=args.config,
        tasks_path=args.tasks,
        team_id=args.team_id,
        headless_mode=args.headless,
        dry_run=args.dry_run
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
