"""
Orchestrator Telemetry Collector

This module runs as a background thread in the orchestrator subprocess to collect
and report telemetry data about the running CrewAI agents back to the Claude-Nine API.

It collects:
- Process metrics (CPU, memory, threads)
- Token usage via CrewAI event bus (LLMStreamChunkEvent for live streaming)
- Git activities by parsing CrewAI logs
- Agent-specific activity by parsing CrewAI's agent outputs
- Task/Agent lifecycle events from CrewAI event bus

CrewAI Event Bus Integration:
- LLMStreamChunkEvent: Live token streaming as they're generated
- LLMCallStartedEvent/LLMCallCompletedEvent: LLM call lifecycle
- AgentExecutionStartedEvent/AgentExecutionCompletedEvent: Agent lifecycle
- TaskStartedEvent/TaskCompletedEvent: Task lifecycle
- ToolUsageStartedEvent/ToolUsageFinishedEvent: Tool usage tracking
"""

import os
import json
import psutil
import threading
import time
import logging
import re
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, UTC
from dataclasses import dataclass, asdict, field
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


@dataclass
class AgentTelemetrySnapshot:
    """Complete telemetry snapshot for an agent"""
    agent_name: str
    timestamp: str
    status: str  # "working" | "idle" | "completed" | "error"
    current_task: Optional[str] = None
    current_action: Optional[str] = None  # What the agent is doing right now
    files_read: List[str] = None
    files_written: List[str] = None
    tool_calls: List[Dict[str, Any]] = None
    token_usage: Optional[TokenUsage] = None
    process_metrics: Optional[ProcessMetrics] = None

    def __post_init__(self):
        if self.files_read is None:
            self.files_read = []
        if self.files_written is None:
            self.files_written = []
        if self.tool_calls is None:
            self.tool_calls = []


class TelemetryCollector:
    """
    Background telemetry collector for orchestrator subprocess.

    Runs in a separate thread and collects metrics about:
    - Process resource usage
    - Agent activity (from CrewAI logs)
    - Token usage per agent
    - Git operations per agent
    - Tool calls and file operations

    Supports both API reporting and file-based output for headless mode.
    """

    def __init__(
        self,
        team_id: str,
        agent_names: List[str],
        api_url: str = "http://localhost:8000",
        check_interval: int = 2,
        output_dir: Optional[Path] = None,
        headless_mode: bool = False
    ):
        """
        Initialize the telemetry collector.

        Args:
            team_id: Team ID for API reporting
            agent_names: List of agent names to track
            api_url: URL of Claude-Nine API
            check_interval: How often to collect and report (seconds)
            output_dir: Directory for file-based telemetry output (headless mode)
            headless_mode: If True, skip API reporting and write to files only
        """
        self.team_id = team_id
        self.agent_names = agent_names
        self.api_url = api_url
        self.check_interval = check_interval
        self.headless_mode = headless_mode

        # Set up output directory for file-based telemetry
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path.cwd() / ".agent-workspace" / "telemetry"

        if headless_mode or output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Telemetry output directory: {self.output_dir}")

        # Our own PID
        self.pid = os.getpid()
        self.process = psutil.Process(self.pid)

        # Running state
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.start_time = datetime.now(UTC)

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

        # Enhanced tracking for more valuable telemetry
        self.agent_status: Dict[str, str] = {name: "idle" for name in agent_names}
        self.agent_current_task: Dict[str, str] = {name: "" for name in agent_names}
        self.agent_current_action: Dict[str, str] = {name: "" for name in agent_names}
        self.agent_files_read: Dict[str, List[str]] = defaultdict(list)
        self.agent_files_written: Dict[str, List[str]] = defaultdict(list)
        self.agent_tool_calls: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Current agent context (for log parsing)
        self.current_agent: Optional[str] = None

        # Log buffer for parsing
        self.log_buffer: List[str] = []
        self.max_log_buffer = 1000

        # Telemetry event log (for file output)
        self.telemetry_events: List[Dict[str, Any]] = []

        # CrewAI event bus subscription state
        self._event_bus_connected = False
        self._event_handlers: List[Callable] = []

        # Live streaming token tracking (updated per-chunk from event bus)
        self.agent_live_tokens: Dict[str, int] = {name: 0 for name in agent_names}
        self.agent_current_llm_call: Dict[str, Dict[str, Any]] = {}

        # Additional event-driven tracking
        self.agent_tool_in_progress: Dict[str, Optional[str]] = {name: None for name in agent_names}
        self.agent_task_description: Dict[str, str] = {name: "" for name in agent_names}

        logger.info(f"Initialized telemetry collector for team {team_id}")
        logger.info(f"Tracking {len(agent_names)} agents: {', '.join(agent_names)}")
        if headless_mode:
            logger.info("Running in headless mode - telemetry will be written to files")

    def start(self):
        """Start the telemetry collection thread and connect to CrewAI event bus."""
        if self.running:
            logger.warning("Telemetry collector already running")
            return

        self.running = True
        
        # Connect to CrewAI event bus for live token streaming
        self._connect_to_event_bus()
        
        self.thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.thread.start()
        logger.info("Telemetry collector started")

    def _connect_to_event_bus(self):
        """
        Connect to the CrewAI event bus for live event streaming.
        
        Subscribes to:
        - LLMStreamChunkEvent: Live token streaming as they're generated
        - LLMCallStartedEvent/LLMCallCompletedEvent: LLM call lifecycle with token counts
        - AgentExecutionStartedEvent/AgentExecutionCompletedEvent: Agent lifecycle
        - TaskStartedEvent/TaskCompletedEvent: Task lifecycle
        - ToolUsageStartedEvent/ToolUsageFinishedEvent: Tool usage tracking
        """
        try:
            # Import CrewAI event bus and event types
            from crewai.utilities.events import crewai_event_bus
            
            # Try to import event types - these may vary by CrewAI version
            try:
                from crewai.utilities.events.events import (
                    LLMStreamChunkEvent,
                    LLMCallStartedEvent,
                    LLMCallCompletedEvent,
                    AgentExecutionStartedEvent,
                    AgentExecutionCompletedEvent,
                    TaskStartedEvent,
                    TaskCompletedEvent,
                    ToolUsageStartedEvent,
                    ToolUsageFinishedEvent,
                )
                self._has_stream_events = True
            except ImportError:
                # Fallback - some events may not be available in all versions
                logger.warning("Some CrewAI event types not available - using basic events")
                self._has_stream_events = False
                try:
                    from crewai.utilities.events.events import (
                        LLMCallStartedEvent,
                        LLMCallCompletedEvent,
                    )
                except ImportError:
                    logger.warning("LLM events not available in this CrewAI version")
                    return

            # Register event handlers
            def on_llm_stream_chunk(source, event):
                """Handle live token streaming - called for each token/chunk."""
                self._handle_llm_stream_chunk(event)
            
            def on_llm_call_started(source, event):
                """Handle LLM call start."""
                self._handle_llm_call_started(event)
            
            def on_llm_call_completed(source, event):
                """Handle LLM call completion with final token counts."""
                self._handle_llm_call_completed(event)
            
            def on_agent_execution_started(source, event):
                """Handle agent execution start."""
                self._handle_agent_execution_started(event)
            
            def on_agent_execution_completed(source, event):
                """Handle agent execution completion."""
                self._handle_agent_execution_completed(event)
            
            def on_task_started(source, event):
                """Handle task start."""
                self._handle_task_started(event)
            
            def on_task_completed(source, event):
                """Handle task completion."""
                self._handle_task_completed(event)
            
            def on_tool_usage_started(source, event):
                """Handle tool usage start."""
                self._handle_tool_usage_started(event)
            
            def on_tool_usage_finished(source, event):
                """Handle tool usage completion."""
                self._handle_tool_usage_finished(event)

            # Subscribe to events
            if self._has_stream_events:
                crewai_event_bus.on(LLMStreamChunkEvent, on_llm_stream_chunk)
                crewai_event_bus.on(LLMCallStartedEvent, on_llm_call_started)
                crewai_event_bus.on(LLMCallCompletedEvent, on_llm_call_completed)
                crewai_event_bus.on(AgentExecutionStartedEvent, on_agent_execution_started)
                crewai_event_bus.on(AgentExecutionCompletedEvent, on_agent_execution_completed)
                crewai_event_bus.on(TaskStartedEvent, on_task_started)
                crewai_event_bus.on(TaskCompletedEvent, on_task_completed)
                crewai_event_bus.on(ToolUsageStartedEvent, on_tool_usage_started)
                crewai_event_bus.on(ToolUsageFinishedEvent, on_tool_usage_finished)
                
                logger.info("Connected to CrewAI event bus with full event support")
            else:
                crewai_event_bus.on(LLMCallStartedEvent, on_llm_call_started)
                crewai_event_bus.on(LLMCallCompletedEvent, on_llm_call_completed)
                logger.info("Connected to CrewAI event bus with basic LLM events")

            self._event_bus_connected = True
            
        except ImportError as e:
            logger.warning(f"CrewAI event bus not available: {e}")
            logger.info("Falling back to log-based telemetry collection")
            self._event_bus_connected = False
        except Exception as e:
            logger.error(f"Failed to connect to CrewAI event bus: {e}")
            self._event_bus_connected = False

    def _handle_llm_stream_chunk(self, event):
        """
        Handle live token streaming from LLMStreamChunkEvent.
        
        This is called for each token/chunk as it's generated by the LLM,
        allowing real-time token counting before the call completes.
        """
        try:
            chunk = getattr(event, 'chunk', None) or getattr(event, 'content', '')
            agent_name = self._get_agent_from_event(event)
            
            if agent_name and chunk:
                # Estimate tokens from chunk (rough: 1 token ≈ 4 chars for English)
                estimated_tokens = max(1, len(chunk) // 4)
                self.agent_live_tokens[agent_name] = self.agent_live_tokens.get(agent_name, 0) + estimated_tokens
                
                # Update current action to show streaming
                self.agent_current_action[agent_name] = f"Generating response... ({self.agent_live_tokens[agent_name]} tokens)"
                
                logger.debug(f"Stream chunk for {agent_name}: +{estimated_tokens} tokens (total: {self.agent_live_tokens[agent_name]})")
        except Exception as e:
            logger.debug(f"Error handling stream chunk: {e}")

    def _handle_llm_call_started(self, event):
        """Handle LLM call start - track which agent is making an LLM call."""
        try:
            agent_name = self._get_agent_from_event(event)
            model = getattr(event, 'model', 'unknown')
            
            if agent_name:
                self.agent_current_llm_call[agent_name] = {
                    'model': model,
                    'start_time': datetime.now(UTC).isoformat(),
                    'input_tokens': 0,
                    'output_tokens': 0
                }
                self.agent_status[agent_name] = "working"
                self.agent_current_action[agent_name] = f"Calling {model}..."
                
                self.add_activity_log(
                    agent_name=agent_name,
                    level="info",
                    message=f"LLM call started: {model}",
                    source="llm"
                )
                logger.debug(f"LLM call started for {agent_name}: {model}")
        except Exception as e:
            logger.debug(f"Error handling LLM call started: {e}")

    def _handle_llm_call_completed(self, event):
        """
        Handle LLM call completion - capture final token counts.
        
        This event contains the authoritative token counts from the LLM provider.
        """
        try:
            agent_name = self._get_agent_from_event(event)
            
            # Extract token usage from event
            input_tokens = getattr(event, 'input_tokens', 0) or getattr(event, 'prompt_tokens', 0)
            output_tokens = getattr(event, 'output_tokens', 0) or getattr(event, 'completion_tokens', 0)
            model = getattr(event, 'model', 'claude-sonnet-4-5')
            
            # Try to get from usage dict if available
            usage = getattr(event, 'usage', {}) or {}
            if isinstance(usage, dict):
                input_tokens = input_tokens or usage.get('input_tokens', 0) or usage.get('prompt_tokens', 0)
                output_tokens = output_tokens or usage.get('output_tokens', 0) or usage.get('completion_tokens', 0)
            
            if agent_name and (input_tokens > 0 or output_tokens > 0):
                # Update cumulative token usage for this agent
                self.track_token_usage(
                    agent_name=agent_name,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=self._calculate_cost(input_tokens, output_tokens)
                )
                
                # Reset live token counter (we now have accurate count)
                self.agent_live_tokens[agent_name] = 0
                
                # Clear current LLM call
                self.agent_current_llm_call.pop(agent_name, None)
                self.agent_current_action[agent_name] = "Processing response..."
                
                total = self.agent_token_usage[agent_name].total_tokens
                self.add_activity_log(
                    agent_name=agent_name,
                    level="info",
                    message=f"LLM call completed: +{input_tokens + output_tokens} tokens (total: {total})",
                    source="llm"
                )
                logger.debug(f"LLM call completed for {agent_name}: {input_tokens}+{output_tokens} tokens")
        except Exception as e:
            logger.debug(f"Error handling LLM call completed: {e}")

    def _handle_agent_execution_started(self, event):
        """Handle agent execution start."""
        try:
            agent_name = self._get_agent_from_event(event)
            if agent_name:
                self.agent_status[agent_name] = "working"
                self.agent_current_action[agent_name] = "Starting execution..."
                self.add_activity_log(
                    agent_name=agent_name,
                    level="info",
                    message="Agent execution started",
                    source="orchestrator"
                )
                logger.debug(f"Agent execution started: {agent_name}")
        except Exception as e:
            logger.debug(f"Error handling agent execution started: {e}")

    def _handle_agent_execution_completed(self, event):
        """Handle agent execution completion."""
        try:
            agent_name = self._get_agent_from_event(event)
            if agent_name:
                self.agent_status[agent_name] = "completed"
                self.agent_current_action[agent_name] = "Execution completed"
                self.add_activity_log(
                    agent_name=agent_name,
                    level="info",
                    message="Agent execution completed",
                    source="orchestrator"
                )
                logger.debug(f"Agent execution completed: {agent_name}")
        except Exception as e:
            logger.debug(f"Error handling agent execution completed: {e}")

    def _handle_task_started(self, event):
        """Handle task start."""
        try:
            agent_name = self._get_agent_from_event(event)
            task_description = getattr(event, 'description', '') or getattr(event, 'task', '')
            if isinstance(task_description, object) and hasattr(task_description, 'description'):
                task_description = task_description.description
            
            if agent_name:
                self.agent_status[agent_name] = "working"
                self.agent_task_description[agent_name] = str(task_description)[:200]
                self.agent_current_task[agent_name] = str(task_description)[:100]
                self.agent_current_action[agent_name] = "Working on task..."
                self.add_activity_log(
                    agent_name=agent_name,
                    level="info",
                    message=f"Task started: {str(task_description)[:80]}...",
                    source="orchestrator"
                )
                logger.debug(f"Task started for {agent_name}")
        except Exception as e:
            logger.debug(f"Error handling task started: {e}")

    def _handle_task_completed(self, event):
        """Handle task completion."""
        try:
            agent_name = self._get_agent_from_event(event)
            if agent_name:
                self.agent_current_action[agent_name] = "Task completed"
                self.add_activity_log(
                    agent_name=agent_name,
                    level="info",
                    message="Task completed successfully",
                    source="orchestrator"
                )
                logger.debug(f"Task completed for {agent_name}")
        except Exception as e:
            logger.debug(f"Error handling task completed: {e}")

    def _handle_tool_usage_started(self, event):
        """Handle tool usage start."""
        try:
            agent_name = self._get_agent_from_event(event)
            tool_name = getattr(event, 'tool_name', '') or getattr(event, 'tool', 'unknown')
            if isinstance(tool_name, object) and hasattr(tool_name, 'name'):
                tool_name = tool_name.name
            
            if agent_name:
                self.agent_tool_in_progress[agent_name] = str(tool_name)
                self.agent_current_action[agent_name] = f"Using tool: {tool_name}"
                self.add_activity_log(
                    agent_name=agent_name,
                    level="info",
                    message=f"Tool started: {tool_name}",
                    source="orchestrator"
                )
                logger.debug(f"Tool usage started for {agent_name}: {tool_name}")
        except Exception as e:
            logger.debug(f"Error handling tool usage started: {e}")

    def _handle_tool_usage_finished(self, event):
        """Handle tool usage completion."""
        try:
            agent_name = self._get_agent_from_event(event)
            tool_name = getattr(event, 'tool_name', '') or getattr(event, 'tool', 'unknown')
            if isinstance(tool_name, object) and hasattr(tool_name, 'name'):
                tool_name = tool_name.name
            result = getattr(event, 'result', None)
            
            if agent_name:
                # Track the tool call
                self.track_tool_call(
                    agent_name=agent_name,
                    tool_name=str(tool_name),
                    result=str(result)[:200] if result else None
                )
                self.agent_tool_in_progress[agent_name] = None
                self.agent_current_action[agent_name] = f"Tool completed: {tool_name}"
                logger.debug(f"Tool usage finished for {agent_name}: {tool_name}")
        except Exception as e:
            logger.debug(f"Error handling tool usage finished: {e}")

    def _get_agent_from_event(self, event) -> Optional[str]:
        """
        Extract agent name from a CrewAI event.
        
        Events may contain agent info in various ways - try multiple attributes.
        """
        # Try direct agent name
        agent_name = getattr(event, 'agent_name', None)
        if agent_name:
            return self._normalize_agent_name(agent_name)
        
        # Try agent object
        agent = getattr(event, 'agent', None)
        if agent:
            if hasattr(agent, 'name'):
                return self._normalize_agent_name(agent.name)
            if hasattr(agent, 'role'):
                return self._normalize_agent_name(agent.role)
        
        # Try role
        role = getattr(event, 'role', None)
        if role:
            return self._normalize_agent_name(role)
        
        # Fall back to current agent context
        return self.current_agent

    def _normalize_agent_name(self, name: str) -> Optional[str]:
        """Normalize agent name to match our tracked agents."""
        if not name:
            return None
        
        name_lower = name.lower().strip()
        
        # Exact match
        for agent_name in self.agent_names:
            if agent_name.lower() == name_lower:
                return agent_name
        
        # Partial match
        for agent_name in self.agent_names:
            if name_lower in agent_name.lower() or agent_name.lower() in name_lower:
                return agent_name
        
        # If not found in our list, use the first agent as fallback (for single-agent crews)
        if len(self.agent_names) == 1:
            return self.agent_names[0]
        
        return None

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on Claude Sonnet 4.5 pricing."""
        # Sonnet 4.5 pricing (per million tokens)
        cost_per_1m_input = 3.00
        cost_per_1m_output = 15.00
        
        cost_usd = (
            (input_tokens / 1_000_000) * cost_per_1m_input +
            (output_tokens / 1_000_000) * cost_per_1m_output
        )
        return round(cost_usd, 6)

    def stop(self):
        """Stop the telemetry collection thread and write final summary."""
        if not self.running:
            return

        self.running = False
        
        # Disconnect from event bus
        self._disconnect_from_event_bus()
        
        if self.thread:
            self.thread.join(timeout=5)

        # Write final summary
        if self.headless_mode or self.output_dir:
            self._write_final_summary()

    def _disconnect_from_event_bus(self):
        """Disconnect from the CrewAI event bus."""
        if not self._event_bus_connected:
            return
        
        try:
            # Note: pyee-based event buses don't have a clean unsubscribe all
            # The handlers will be cleaned up when the collector is garbage collected
            self._event_bus_connected = False
            logger.info("Disconnected from CrewAI event bus")
        except Exception as e:
            logger.warning(f"Error disconnecting from event bus: {e}")

        logger.info("Telemetry collector stopped")

    def _write_final_summary(self):
        """Write a comprehensive summary of the entire run."""
        try:
            end_time = datetime.now(UTC)
            duration = (end_time - self.start_time).total_seconds()

            summary = {
                "team_id": self.team_id,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "agents": {}
            }

            # Compile per-agent summaries
            total_tokens = 0
            total_cost = 0.0
            total_files_read = 0
            total_files_written = 0
            total_tool_calls = 0

            for agent_name in self.agent_names:
                token_usage = self.agent_token_usage.get(agent_name)
                if token_usage:
                    total_tokens += token_usage.total_tokens
                    total_cost += token_usage.cost_usd

                files_read = len(self.agent_files_read.get(agent_name, []))
                files_written = len(self.agent_files_written.get(agent_name, []))
                tool_calls = len(self.agent_tool_calls.get(agent_name, []))

                total_files_read += files_read
                total_files_written += files_written
                total_tool_calls += tool_calls

                summary["agents"][agent_name] = {
                    "status": self.agent_status.get(agent_name, "unknown"),
                    "token_usage": asdict(token_usage) if token_usage else None,
                    "files_read": files_read,
                    "files_read_list": self.agent_files_read.get(agent_name, []),
                    "files_written": files_written,
                    "files_written_list": self.agent_files_written.get(agent_name, []),
                    "tool_calls": tool_calls,
                    "git_activities": [
                        asdict(a) for a in self.agent_git_activities.get(agent_name, [])
                    ],
                    "log_count": len(self.agent_activity_logs.get(agent_name, []))
                }

            summary["totals"] = {
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "total_files_read": total_files_read,
                "total_files_written": total_files_written,
                "total_tool_calls": total_tool_calls,
                "total_events": len(self.telemetry_events)
            }

            # Write summary file
            summary_file = self.output_dir / "run_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, default=str)

            logger.info(f"Wrote telemetry summary to {summary_file}")
            logger.info(f"Run summary: {summary['totals']}")

        except Exception as e:
            logger.error(f"Failed to write final summary: {e}")

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
        """Report telemetry data for a specific agent to the API and/or files."""
        try:
            # Get current token usage, including live streaming tokens if any
            token_usage = self.agent_token_usage.get(agent_name)
            if token_usage:
                # Build token_data without cost_usd (UI calculates cost)
                token_data = {
                    "model": token_usage.model,
                    "input_tokens": token_usage.input_tokens,
                    "output_tokens": token_usage.output_tokens,
                    "total_tokens": token_usage.total_tokens
                }
                # Add live streaming tokens (estimated, not yet finalized)
                live_tokens = self.agent_live_tokens.get(agent_name, 0)
                if live_tokens > 0:
                    token_data['streaming_tokens'] = live_tokens
                    token_data['total_tokens_with_streaming'] = token_data['total_tokens'] + live_tokens
            else:
                token_data = {
                    "model": "claude-sonnet-4-5",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                }

            # Prepare telemetry payload with enhanced data
            payload = {
                "team_id": self.team_id,
                "agent_name": agent_name,
                "status": self.agent_status.get(agent_name, "unknown"),
                "current_task": self.agent_current_task.get(agent_name, ""),
                "current_action": self.agent_current_action.get(agent_name, ""),
                "process_metrics": asdict(metrics),
                "token_usage": token_data,
                "files_read": self.agent_files_read.get(agent_name, [])[-10:],
                "files_written": self.agent_files_written.get(agent_name, [])[-10:],
                "tool_calls": self.agent_tool_calls.get(agent_name, [])[-10:],
                "tool_in_progress": self.agent_tool_in_progress.get(agent_name),
                "git_activities": [
                    asdict(activity) for activity in self.agent_git_activities[agent_name][-10:]
                ],
                "activity_logs": [
                    asdict(log) for log in self.agent_activity_logs[agent_name][-50:]
                ],
                "timestamp": datetime.now(UTC).isoformat(),
                "heartbeat": True,  # Explicit heartbeat flag for UI
                "event_bus_connected": self._event_bus_connected  # Let UI know if we have live data
            }

            # Store event for file output
            self.telemetry_events.append({
                "type": "agent_update",
                "data": payload
            })

            # Write to file if in headless mode or output dir is set
            if self.headless_mode or self.output_dir:
                self._write_telemetry_to_file(agent_name, payload)

            # Send to API if not in headless mode
            if not self.headless_mode:
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

    def _write_telemetry_to_file(self, agent_name: str, payload: Dict[str, Any]):
        """Write telemetry data to a file for headless mode."""
        try:
            # Write to agent-specific latest file
            agent_file = self.output_dir / f"{agent_name}_latest.json"
            with open(agent_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, default=str)

            # Also append to the agent's event log
            event_log_file = self.output_dir / f"{agent_name}_events.jsonl"
            with open(event_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(payload, default=str) + "\n")

        except Exception as e:
            logger.warning(f"Failed to write telemetry file for {agent_name}: {e}")

    def process_log_line(self, line: str):
        """
        Process a log line from CrewAI stdout/stderr.

        Extracts:
        - Which agent is currently active
        - Git operations
        - Token usage
        - File operations (reads/writes)
        - Tool calls
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
            self.agent_status[self.current_agent] = "working"
            logger.debug(f"Switched context to agent: {self.current_agent}")

        # Parse file read operations
        file_read_patterns = [
            r'Read\s+(.+?)\s+from\s+working\s+directory',
            r'Reading\s+file:\s+(.+)',
            r'git_read_file.*?path["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        ]
        for pattern in file_read_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match and self.current_agent:
                file_path = match.group(1).strip()
                self.track_file_read(self.current_agent, file_path)
                break

        # Parse file write operations
        file_write_patterns = [
            r'Wrote\s+content\s+to\s+(.+)',
            r'Writing\s+file:\s+(.+)',
            r'git_write_file.*?path["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        ]
        for pattern in file_write_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match and self.current_agent:
                file_path = match.group(1).strip()
                self.track_file_write(self.current_agent, file_path)
                break

        # Parse tool usage
        tool_patterns = [
            r'Using\s+tool:\s+(.+)',
            r'Tool\s+call:\s+(.+)',
            r'Executing\s+(.+?)\s+tool',
        ]
        for pattern in tool_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match and self.current_agent:
                tool_name = match.group(1).strip()
                self.track_tool_call(self.current_agent, tool_name)
                break

        # Parse agent completion
        completion_patterns = [
            r'Task\s+completed',
            r'Agent\s+finished',
            r'Crew\s+Execution\s+Completed',
        ]
        for pattern in completion_patterns:
            if re.search(pattern, line, re.IGNORECASE) and self.current_agent:
                self.agent_status[self.current_agent] = "completed"
                break

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

    def track_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None
    ):
        """
        Track a tool call made by an agent.

        Args:
            agent_name: Name of the agent
            tool_name: Name of the tool being called
            arguments: Tool arguments (optional)
            result: Tool result summary (optional)
        """
        tool_call = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tool": tool_name,
            "arguments": arguments or {},
            "result": result[:200] if result else None
        }

        self.agent_tool_calls[agent_name].append(tool_call)

        # Keep only last 50 per agent
        if len(self.agent_tool_calls[agent_name]) > 50:
            self.agent_tool_calls[agent_name].pop(0)

        # Update current action
        self.agent_current_action[agent_name] = f"Using {tool_name}"

        logger.debug(f"Tracked tool call for {agent_name}: {tool_name}")

    def track_file_read(self, agent_name: str, file_path: str):
        """Track a file read operation by an agent."""
        if file_path not in self.agent_files_read[agent_name]:
            self.agent_files_read[agent_name].append(file_path)
        self.agent_current_action[agent_name] = f"Reading {Path(file_path).name}"
        logger.debug(f"Tracked file read for {agent_name}: {file_path}")

    def track_file_write(self, agent_name: str, file_path: str):
        """Track a file write operation by an agent."""
        if file_path not in self.agent_files_written[agent_name]:
            self.agent_files_written[agent_name].append(file_path)
        self.agent_current_action[agent_name] = f"Writing {Path(file_path).name}"
        logger.debug(f"Tracked file write for {agent_name}: {file_path}")

    def set_agent_status(self, agent_name: str, status: str, task: Optional[str] = None):
        """
        Update an agent's status.

        Args:
            agent_name: Name of the agent
            status: New status (idle, working, completed, error)
            task: Current task description (optional)
        """
        self.agent_status[agent_name] = status
        if task:
            self.agent_current_task[agent_name] = task

        logger.debug(f"Set status for {agent_name}: {status}")

    def set_agent_action(self, agent_name: str, action: str):
        """Update what an agent is currently doing."""
        self.agent_current_action[agent_name] = action
        logger.debug(f"Set action for {agent_name}: {action}")


# Global telemetry collector instance
_global_collector: Optional[TelemetryCollector] = None


def initialize_telemetry(
    team_id: str,
    agent_names: List[str],
    api_url: str = "http://localhost:8000",
    check_interval: int = 2,
    output_dir: Optional[Path] = None,
    headless_mode: bool = False
) -> TelemetryCollector:
    """
    Initialize and start the global telemetry collector.

    Args:
        team_id: Team ID for API reporting
        agent_names: List of agent names to track
        api_url: URL of Claude-Nine API
        check_interval: How often to collect and report (seconds)
        output_dir: Directory for file-based telemetry output
        headless_mode: If True, skip API reporting and write to files only

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
        check_interval=check_interval,
        output_dir=output_dir,
        headless_mode=headless_mode
    )
    _global_collector.start()

    logger.info(f"Global telemetry collector initialized for team {team_id}")
    if headless_mode:
        logger.info(f"Telemetry will be written to: {_global_collector.output_dir}")
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
