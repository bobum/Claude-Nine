"""
Orchestrator Telemetry Collector

This module runs as a background thread in the orchestrator subprocess to collect
and report telemetry data about the running CrewAI agents back to the Claude-Nine API.

It collects:
- Process metrics (CPU, memory, threads)
- Token usage by intercepting Anthropic API calls
- Git activities by parsing CrewAI logs
- Agent-specific activity by parsing CrewAI's agent outputs
"""

import os
import psutil
import threading
import time
import logging
import re
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ProcessMetrics:
    """Process resource usage metrics"""
    pid: int
    cpu_percent: float
    memory_mb: float
    threads: int
    status: str


@dataclass
class GitActivity:
    """Git operation activity"""
    operation: str  # "branch_create" | "commit" | "checkout" | "merge"
    branch: Optional[str] = None
    message: Optional[str] = None
    files_changed: Optional[int] = None
    timestamp: Optional[str] = None
    agent_name: Optional[str] = None  # Which agent performed this


@dataclass
class TokenUsage:
    """LLM token usage tracking per agent"""
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass
class ActivityLog:
    """Activity log entry"""
    timestamp: str
    level: str  # "info" | "warning" | "error"
    message: str
    source: str  # "orchestrator" | "git" | "llm" | "system"
    agent_name: Optional[str] = None


class TelemetryCollector:
    """
    Background telemetry collector for orchestrator subprocess.

    Runs in a separate thread and collects metrics about:
    - Process resource usage
    - Agent activity (from CrewAI logs)
    - Token usage per agent
    - Git operations per agent
    """

    def __init__(
        self,
        team_id: str,
        agent_names: List[str],
        api_url: str = "http://localhost:8000",
        check_interval: int = 2
    ):
        """
        Initialize the telemetry collector.

        Args:
            team_id: Team ID for API reporting
            agent_names: List of agent names to track
            api_url: URL of Claude-Nine API
            check_interval: How often to collect and report (seconds)
        """
        self.team_id = team_id
        self.agent_names = agent_names
        self.api_url = api_url
        self.check_interval = check_interval

        # Our own PID
        self.pid = os.getpid()
        self.process = psutil.Process(self.pid)

        # Running state
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Per-agent tracking
        self.agent_token_usage: Dict[str, TokenUsage] = {
            name: TokenUsage(
                model="claude-sonnet-4-5",
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0
            )
            for name in agent_names
        }
        self.agent_git_activities: Dict[str, List[GitActivity]] = defaultdict(list)
        self.agent_activity_logs: Dict[str, List[ActivityLog]] = defaultdict(list)

        # Current agent context (for log parsing)
        self.current_agent: Optional[str] = None

        # Log buffer for parsing
        self.log_buffer: List[str] = []
        self.max_log_buffer = 1000

        logger.info(f"Initialized telemetry collector for team {team_id}")
        logger.info(f"Tracking {len(agent_names)} agents: {', '.join(agent_names)}")

    def start(self):
        """Start the telemetry collection thread."""
        if self.running:
            logger.warning("Telemetry collector already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.thread.start()
        logger.info("Telemetry collector started")

    def stop(self):
        """Stop the telemetry collection thread."""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Telemetry collector stopped")

    def _collection_loop(self):
        """Main collection loop running in background thread."""
        logger.info("Telemetry collection loop started")

        while self.running:
            try:
                # Collect process metrics
                metrics = self._collect_process_metrics()

                # Report telemetry for each agent
                for agent_name in self.agent_names:
                    self._report_agent_telemetry(agent_name, metrics)

                # Sleep until next collection
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in telemetry collection loop: {e}", exc_info=True)
                time.sleep(self.check_interval)

    def _collect_process_metrics(self) -> ProcessMetrics:
        """Collect current process metrics."""
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            threads = self.process.num_threads()
            status = self.process.status()

            return ProcessMetrics(
                pid=self.pid,
                cpu_percent=round(cpu_percent, 2),
                memory_mb=round(memory_mb, 2),
                threads=threads,
                status=status
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Failed to collect process metrics: {e}")
            return ProcessMetrics(
                pid=self.pid,
                cpu_percent=0.0,
                memory_mb=0.0,
                threads=0,
                status="unknown"
            )

    def _report_agent_telemetry(self, agent_name: str, metrics: ProcessMetrics):
        """Report telemetry data for a specific agent to the API."""
        try:
            # Prepare telemetry payload
            payload = {
                "team_id": self.team_id,
                "agent_name": agent_name,
                "process_metrics": asdict(metrics),
                "token_usage": asdict(self.agent_token_usage[agent_name]),
                "git_activities": [
                    asdict(activity) for activity in self.agent_git_activities[agent_name][-10:]
                ],
                "activity_logs": [
                    asdict(log) for log in self.agent_activity_logs[agent_name][-50:]
                ],
                "timestamp": datetime.now(UTC).isoformat()
            }

            # Send to API (synchronous - we're in a thread)
            # Note: Using httpx instead of requests for better async support later
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.api_url}/api/telemetry/agent/{agent_name}",
                    json=payload
                )

                if response.status_code != 200:
                    logger.warning(
                        f"API returned status {response.status_code} for agent {agent_name}"
                    )

        except Exception as e:
            logger.warning(f"Failed to report telemetry for {agent_name}: {e}")

    def process_log_line(self, line: str):
        """
        Process a log line from CrewAI stdout/stderr.

        Extracts:
        - Which agent is currently active
        - Git operations
        - Token usage
        - General activity
        """
        # Add to buffer
        self.log_buffer.append(line)
        if len(self.log_buffer) > self.max_log_buffer:
            self.log_buffer.pop(0)

        # Detect current agent context
        agent_pattern = r"Agent:\s+(.+?)(?:\n|\s+working)"
        agent_match = re.search(agent_pattern, line, re.IGNORECASE)
        if agent_match:
            self.current_agent = agent_match.group(1).strip()
            logger.debug(f"Switched context to agent: {self.current_agent}")

        # Parse git activity
        git_activity = self._parse_git_activity(line)
        if git_activity and self.current_agent:
            git_activity.agent_name = self.current_agent
            self.agent_git_activities[self.current_agent].append(git_activity)
            # Keep only last 20 per agent
            if len(self.agent_git_activities[self.current_agent]) > 20:
                self.agent_git_activities[self.current_agent].pop(0)

        # Parse token usage
        token_usage = self._parse_token_usage(line)
        if token_usage and self.current_agent:
            # Update cumulative totals
            current = self.agent_token_usage[self.current_agent]
            current.input_tokens += token_usage.input_tokens
            current.output_tokens += token_usage.output_tokens
            current.total_tokens += token_usage.total_tokens
            current.cost_usd += token_usage.cost_usd

        # Add to activity log
        if self.current_agent:
            level = self._determine_log_level(line)
            activity = ActivityLog(
                timestamp=datetime.now(UTC).isoformat(),
                level=level,
                message=line.strip()[:500],  # Truncate long lines
                source="orchestrator",
                agent_name=self.current_agent
            )
            self.agent_activity_logs[self.current_agent].append(activity)
            # Keep only last 100 per agent
            if len(self.agent_activity_logs[self.current_agent]) > 100:
                self.agent_activity_logs[self.current_agent].pop(0)

    def _parse_git_activity(self, line: str) -> Optional[GitActivity]:
        """Parse a log line for git activity."""
        git_patterns = {
            r'Creating branch[:\s]+([^\s]+)': 'branch_create',
            r'Committed\s+(\d+)\s+files?': 'commit',
            r'Switched to branch[:\s]+([^\s]+)': 'checkout',
            r'Merged branch[:\s]+([^\s]+)': 'merge',
            r'git\s+branch\s+([^\s]+)': 'branch_create',
            r'git\s+commit.*-m\s+"([^"]+)"': 'commit',
        }

        for pattern, operation in git_patterns.items():
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                activity = GitActivity(
                    operation=operation,
                    timestamp=datetime.now(UTC).isoformat()
                )

                # Extract details based on operation
                if operation == 'branch_create':
                    activity.branch = match.group(1)
                elif operation == 'commit':
                    if match.group(1).isdigit():
                        activity.files_changed = int(match.group(1))
                    else:
                        activity.message = match.group(1)
                elif operation in ['checkout', 'merge']:
                    activity.branch = match.group(1)

                return activity

        return None

    def _parse_token_usage(self, line: str) -> Optional[TokenUsage]:
        """Parse a log line for token usage."""
        # Anthropic/CrewAI token usage patterns
        token_patterns = [
            r'Token usage:\s+(\d+)\s+input,?\s+(\d+)\s+output',
            r'Tokens:\s+(\d+)\s+in,?\s+(\d+)\s+out',
            r'input_tokens[:\s]+(\d+).*output_tokens[:\s]+(\d+)',
            r'usage.*input.*?(\d+).*output.*?(\d+)',
        ]

        for pattern in token_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                input_tokens = int(match.group(1))
                output_tokens = int(match.group(2))

                # Sonnet 4.5 pricing (per million tokens)
                cost_per_1m_input = 3.00
                cost_per_1m_output = 15.00

                cost_usd = (
                    (input_tokens / 1_000_000) * cost_per_1m_input +
                    (output_tokens / 1_000_000) * cost_per_1m_output
                )

                return TokenUsage(
                    model="claude-sonnet-4-5",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    cost_usd=round(cost_usd, 6)
                )

        return None

    def _determine_log_level(self, line: str) -> str:
        """Determine log level from line content."""
        line_lower = line.lower()
        if "error" in line_lower or "exception" in line_lower or "failed" in line_lower:
            return "error"
        elif "warning" in line_lower or "warn" in line_lower:
            return "warning"
        else:
            return "info"

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of collected telemetry."""
        return {
            "team_id": self.team_id,
            "tracked_agents": self.agent_names,
            "total_tokens": sum(
                usage.total_tokens for usage in self.agent_token_usage.values()
            ),
            "total_cost": sum(
                usage.cost_usd for usage in self.agent_token_usage.values()
            ),
            "total_git_activities": sum(
                len(activities) for activities in self.agent_git_activities.values()
            ),
            "total_logs": sum(
                len(logs) for logs in self.agent_activity_logs.values()
            )
        }

    def track_token_usage(
        self,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ):
        """
        Manually track token usage for an agent.

        Args:
            agent_name: Name of the agent
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
        """
        if agent_name not in self.agent_token_usage:
            self.agent_token_usage[agent_name] = TokenUsage(
                model=model,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0
            )

        current = self.agent_token_usage[agent_name]
        current.model = model  # Update to latest model
        current.input_tokens += input_tokens
        current.output_tokens += output_tokens
        current.total_tokens += (input_tokens + output_tokens)
        current.cost_usd += cost_usd

        logger.debug(
            f"Tracked {input_tokens + output_tokens} tokens for {agent_name} "
            f"(${cost_usd:.6f})"
        )

    def track_git_activity(
        self,
        agent_name: str,
        operation: str,
        branch: Optional[str] = None,
        message: Optional[str] = None,
        files_changed: Optional[int] = None
    ):
        """
        Manually track a git activity for an agent.

        Args:
            agent_name: Name of the agent
            operation: Git operation type (branch_create, commit, checkout, merge)
            branch: Branch name (optional)
            message: Commit message (optional)
            files_changed: Number of files changed (optional)
        """
        activity = GitActivity(
            operation=operation,
            branch=branch,
            message=message,
            files_changed=files_changed,
            timestamp=datetime.now(UTC).isoformat(),
            agent_name=agent_name
        )

        self.agent_git_activities[agent_name].append(activity)

        # Keep only last 20 per agent
        if len(self.agent_git_activities[agent_name]) > 20:
            self.agent_git_activities[agent_name].pop(0)

        logger.debug(f"Tracked git activity for {agent_name}: {operation}")

    def add_activity_log(
        self,
        agent_name: str,
        level: str,
        message: str,
        source: str = "orchestrator"
    ):
        """
        Manually add an activity log entry for an agent.

        Args:
            agent_name: Name of the agent
            level: Log level (info, warning, error)
            message: Log message
            source: Source of the log (orchestrator, git, llm, system)
        """
        activity = ActivityLog(
            timestamp=datetime.now(UTC).isoformat(),
            level=level,
            message=message[:500],  # Truncate long messages
            source=source,
            agent_name=agent_name
        )

        self.agent_activity_logs[agent_name].append(activity)

        # Keep only last 100 per agent
        if len(self.agent_activity_logs[agent_name]) > 100:
            self.agent_activity_logs[agent_name].pop(0)

        logger.debug(f"Added activity log for {agent_name}: [{level}] {message[:50]}")


# Global telemetry collector instance
_global_collector: Optional[TelemetryCollector] = None


def initialize_telemetry(
    team_id: str,
    agent_names: List[str],
    api_url: str = "http://localhost:8000",
    check_interval: int = 2
) -> TelemetryCollector:
    """
    Initialize and start the global telemetry collector.

    Args:
        team_id: Team ID for API reporting
        agent_names: List of agent names to track
        api_url: URL of Claude-Nine API
        check_interval: How often to collect and report (seconds)

    Returns:
        TelemetryCollector: The initialized collector instance
    """
    global _global_collector

    if _global_collector is not None:
        logger.warning("Telemetry collector already initialized")
        return _global_collector

    _global_collector = TelemetryCollector(
        team_id=team_id,
        agent_names=agent_names,
        api_url=api_url,
        check_interval=check_interval
    )
    _global_collector.start()

    logger.info(f"Global telemetry collector initialized for team {team_id}")
    return _global_collector


def get_telemetry_collector() -> Optional[TelemetryCollector]:
    """
    Get the global telemetry collector instance.

    Returns:
        Optional[TelemetryCollector]: The collector instance, or None if not initialized
    """
    return _global_collector


def shutdown_telemetry():
    """Shutdown the global telemetry collector."""
    global _global_collector

    if _global_collector is None:
        return

    _global_collector.stop()
    _global_collector = None
    logger.info("Global telemetry collector shutdown")
