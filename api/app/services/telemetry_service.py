"""
Telemetry Service - Real-time monitoring of agent processes

This module provides real-time telemetry collection for orchestrator subprocesses,
including process metrics, git activity, token usage, and activity logs.
"""

import psutil
import asyncio
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from pathlib import Path

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


@dataclass
class TokenUsage:
    """LLM token usage tracking"""
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


@dataclass
class AgentTelemetry:
    """Aggregated agent telemetry data"""
    agent_id: str
    team_id: str
    process_metrics: Optional[ProcessMetrics]
    git_activities: List[GitActivity]
    token_usage: Optional[TokenUsage]
    activity_logs: List[ActivityLog]
    last_updated: str


class ProcessMetricsCollector:
    """Collects process resource metrics using psutil"""

    def __init__(self, pid: int):
        self.pid = pid
        try:
            self.process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} not found")
            self.process = None

    async def collect_metrics(self) -> Optional[ProcessMetrics]:
        """Collect current process metrics"""
        if not self.process or not self.process.is_running():
            return None

        try:
            # Get metrics
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
            logger.warning(f"Failed to collect metrics for PID {self.pid}: {e}")
            return None


class GitActivityMonitor:
    """Monitors git operations from orchestrator output"""

    # Patterns to match git operations in logs
    GIT_PATTERNS = {
        r'Creating branch[:\s]+([^\s]+)': 'branch_create',
        r'Committed\s+(\d+)\s+files?': 'commit',
        r'Switched to branch[:\s]+([^\s]+)': 'checkout',
        r'Merged branch[:\s]+([^\s]+)': 'merge',
        r'git\s+branch\s+([^\s]+)': 'branch_create',
        r'git\s+commit.*-m\s+"([^"]+)"': 'commit',
    }

    def parse_log_line(self, line: str) -> Optional[GitActivity]:
        """Parse a log line for git activity"""
        for pattern, operation in self.GIT_PATTERNS.items():
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


class TokenUsageTracker:
    """Tracks LLM token usage from orchestrator output"""

    # Pattern to match token usage in CrewAI output
    TOKEN_PATTERNS = [
        r'Token usage:\s+(\d+)\s+input,\s+(\d+)\s+output',
        r'Tokens:\s+(\d+)\s+in,\s+(\d+)\s+out',
        r'input_tokens[:\s]+(\d+).*output_tokens[:\s]+(\d+)',
    ]

    # Sonnet 4.5 pricing (as of 2025)
    COST_PER_1M_INPUT = 3.00
    COST_PER_1M_OUTPUT = 15.00

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def parse_token_usage(self, line: str) -> Optional[TokenUsage]:
        """Parse a log line for token usage"""
        for pattern in self.TOKEN_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                input_tokens = int(match.group(1))
                output_tokens = int(match.group(2))

                # Update totals
                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens

                # Calculate cost
                cost_usd = (
                    (input_tokens / 1_000_000) * self.COST_PER_1M_INPUT +
                    (output_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT
                )

                return TokenUsage(
                    model="claude-sonnet-4-5",
                    input_tokens=self.total_input_tokens,
                    output_tokens=self.total_output_tokens,
                    total_tokens=self.total_input_tokens + self.total_output_tokens,
                    cost_usd=round(cost_usd, 6)
                )
        return None

    def get_total_usage(self) -> TokenUsage:
        """Get total token usage"""
        total_cost = (
            (self.total_input_tokens / 1_000_000) * self.COST_PER_1M_INPUT +
            (self.total_output_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT
        )

        return TokenUsage(
            model="claude-sonnet-4-5",
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            total_tokens=self.total_input_tokens + self.total_output_tokens,
            cost_usd=round(total_cost, 6)
        )


class ActivityLogBuffer:
    """Maintains a rolling buffer of activity logs"""

    def __init__(self, max_size: int = 100):
        self.logs: List[ActivityLog] = []
        self.max_size = max_size

    def add_log(self, level: str, message: str, source: str):
        """Add a log entry to the buffer"""
        log = ActivityLog(
            timestamp=datetime.now(UTC).isoformat(),
            level=level,
            message=message.strip(),
            source=source
        )
        self.logs.append(log)

        # Maintain max size
        if len(self.logs) > self.max_size:
            self.logs.pop(0)

    def get_recent_logs(self, count: int = 50) -> List[ActivityLog]:
        """Get the most recent logs"""
        return self.logs[-count:]

    def clear(self):
        """Clear all logs"""
        self.logs.clear()


class AgentMonitor:
    """Monitors a single agent's orchestrator process"""

    def __init__(self, team_id: str, agent_id: str, pid: int):
        self.team_id = team_id
        self.agent_id = agent_id
        self.pid = pid
        self.running = False

        # Initialize collectors
        self.metrics_collector = ProcessMetricsCollector(pid)
        self.git_monitor = GitActivityMonitor()
        self.token_tracker = TokenUsageTracker()
        self.activity_buffer = ActivityLogBuffer()

        # Track activities
        self.git_activities: List[GitActivity] = []
        self.current_token_usage: Optional[TokenUsage] = None
        self.current_metrics: Optional[ProcessMetrics] = None

    async def run(self):
        """Main monitoring loop"""
        self.running = True
        logger.info(f"Started monitoring agent {self.agent_id} (PID: {self.pid})")

        while self.running:
            try:
                # Collect process metrics every 2 seconds
                metrics = await self.metrics_collector.collect_metrics()
                if metrics:
                    self.current_metrics = metrics

                    # Broadcast metrics update
                    from ..websocket import notify_agent_telemetry
                    await notify_agent_telemetry(
                        self.agent_id,
                        self.team_id,
                        "metrics_update",
                        {"process_metrics": asdict(metrics)}
                    )

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error in monitoring loop for agent {self.agent_id}: {e}")
                await asyncio.sleep(2)

    def stop(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info(f"Stopped monitoring agent {self.agent_id}")

    def process_log_line(self, line: str, source: str = "orchestrator"):
        """Process a log line from stdout/stderr"""
        # Parse for git activity
        git_activity = self.git_monitor.parse_log_line(line)
        if git_activity:
            self.git_activities.append(git_activity)
            # Keep only last 10 activities
            if len(self.git_activities) > 10:
                self.git_activities.pop(0)

        # Parse for token usage
        token_usage = self.token_tracker.parse_token_usage(line)
        if token_usage:
            self.current_token_usage = token_usage

        # Add to activity log
        level = "info"
        if "error" in line.lower():
            level = "error"
        elif "warning" in line.lower():
            level = "warning"

        self.activity_buffer.add_log(level, line, source)

    def get_telemetry(self) -> AgentTelemetry:
        """Get current telemetry snapshot"""
        return AgentTelemetry(
            agent_id=self.agent_id,
            team_id=self.team_id,
            process_metrics=self.current_metrics,
            git_activities=self.git_activities[-10:],  # Last 10
            token_usage=self.current_token_usage or self.token_tracker.get_total_usage(),
            activity_logs=self.activity_buffer.get_recent_logs(50),  # Last 50
            last_updated=datetime.now(UTC).isoformat()
        )


class TelemetryService:
    """Main telemetry service managing all agent monitors"""

    def __init__(self):
        self.active_monitors: Dict[str, AgentMonitor] = {}
        self._monitor_tasks: Dict[str, asyncio.Task] = {}

    def start_monitoring(self, team_id: str, agent_id: str, pid: int):
        """Start monitoring an agent's orchestrator process"""
        if agent_id in self.active_monitors:
            logger.warning(f"Agent {agent_id} is already being monitored")
            return

        # Create and start monitor
        monitor = AgentMonitor(team_id, agent_id, pid)
        self.active_monitors[agent_id] = monitor

        # Start monitoring loop
        task = asyncio.create_task(monitor.run())
        self._monitor_tasks[agent_id] = task

        logger.info(f"Started telemetry monitoring for agent {agent_id} (PID: {pid})")

    def stop_monitoring(self, agent_id: str):
        """Stop monitoring an agent"""
        if agent_id not in self.active_monitors:
            return

        # Stop the monitor
        monitor = self.active_monitors[agent_id]
        monitor.stop()

        # Cancel the task
        if agent_id in self._monitor_tasks:
            self._monitor_tasks[agent_id].cancel()
            del self._monitor_tasks[agent_id]

        # Remove from active monitors
        del self.active_monitors[agent_id]

        logger.info(f"Stopped telemetry monitoring for agent {agent_id}")

    def get_agent_monitor(self, agent_id: str) -> Optional[AgentMonitor]:
        """Get the monitor for a specific agent"""
        return self.active_monitors.get(agent_id)

    def get_telemetry(self, agent_id: str) -> Optional[AgentTelemetry]:
        """Get telemetry data for a specific agent"""
        monitor = self.get_agent_monitor(agent_id)
        return monitor.get_telemetry() if monitor else None

    def get_all_telemetry(self) -> Dict[str, AgentTelemetry]:
        """Get telemetry data for all monitored agents"""
        return {
            agent_id: monitor.get_telemetry()
            for agent_id, monitor in self.active_monitors.items()
        }


# Global singleton instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get the global telemetry service instance"""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service
