"""Telemetry endpoints for agent monitoring."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..websocket import notify_agent_telemetry

router = APIRouter()

# Test counter for mock telemetry - TEMPORARY FOR TESTING
_test_counter = 0


class ProcessMetrics(BaseModel):
    """Process resource usage metrics"""
    pid: int
    cpu_percent: float
    memory_mb: float
    threads: int
    status: str


class GitActivity(BaseModel):
    """Git operation activity"""
    operation: str
    branch: Optional[str] = None
    message: Optional[str] = None
    files_changed: Optional[int] = None
    timestamp: Optional[str] = None
    agent_name: Optional[str] = None


class TokenUsage(BaseModel):
    """LLM token usage tracking"""
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    # Live streaming tokens (estimated, not yet finalized)
    streaming_tokens: Optional[int] = None
    total_tokens_with_streaming: Optional[int] = None


class ActivityLog(BaseModel):
    """Activity log entry"""
    timestamp: str
    level: str
    message: str
    source: str
    agent_name: Optional[str] = None


class ToolCall(BaseModel):
    """Tool call record"""
    timestamp: str
    tool: str
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[str] = None


class AgentTelemetryData(BaseModel):
    """Agent telemetry data from orchestrator"""
    team_id: str
    agent_name: str
    status: Optional[str] = "unknown"
    current_task: Optional[str] = ""
    current_action: Optional[str] = ""
    process_metrics: ProcessMetrics
    token_usage: TokenUsage
    git_activities: List[GitActivity] = []
    activity_logs: List[ActivityLog] = []
    files_read: Optional[List[str]] = None
    files_written: Optional[List[str]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_in_progress: Optional[str] = None
    timestamp: str
    heartbeat: Optional[bool] = True
    event_bus_connected: Optional[bool] = False


@router.post("/agent/{agent_name}")
async def receive_agent_telemetry(
    agent_name: str,
    data: AgentTelemetryData
):
    """
    Receive telemetry data from orchestrator subprocess for a specific agent.

    This endpoint is called by the telemetry collector thread running in the
    orchestrator subprocess. It receives metrics, token usage, git activities,
    and activity logs for each agent.

    The data is then broadcast via WebSocket to connected dashboard clients.
    
    Enhanced data includes:
    - Live streaming token counts (before LLM call completes)
    - Current task and action descriptions
    - Tool usage in progress
    - Event bus connection status
    - Heartbeat timestamp
    """
    try:
        # Broadcast telemetry to WebSocket clients
        await notify_agent_telemetry(
            agent_id=agent_name,  # Using agent_name as agent_id for now
            team_id=data.team_id,
            event="metrics_update",
            data={
                "agent_name": agent_name,
                "status": data.status,
                "current_task": data.current_task,
                "current_action": data.current_action,
                "process_metrics": data.process_metrics.dict(),
                "token_usage": data.token_usage.dict(),
                "git_activities": [activity.dict() for activity in data.git_activities],
                "activity_logs": [log.dict() for log in data.activity_logs],
                "files_read": data.files_read or [],
                "files_written": data.files_written or [],
                "tool_calls": data.tool_calls or [],
                "tool_in_progress": data.tool_in_progress,
                "timestamp": data.timestamp,
                "heartbeat": data.heartbeat,
                "event_bus_connected": data.event_bus_connected
            }
        )

        return {
            "status": "success",
            "message": f"Telemetry received for agent {agent_name}",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process telemetry: {str(e)}"
        )


@router.get("/agent/{agent_name}")
async def get_agent_telemetry(
    agent_name: str,
    team_id: str = "f398aeda-5257-45ec-a09f-b02d0de402ae",
    simulate_streaming: bool = False
):
    """
    TEMPORARY TEST MODE: Sends mock telemetry via WebSocket to test the connection.

    This allows testing WebSocket delivery without running the full orchestrator.
    Call this endpoint (e.g., http://localhost:8000/api/telemetry/agent/DevAgent)
    and watch the dashboard to see if the mock data appears in the agent card.

    Query params:
    - team_id: Team ID for WebSocket routing
    - simulate_streaming: If true, simulates live token streaming with streaming_tokens

    TODO: Replace with actual cached telemetry data retrieval in production.
    """
    import random
    global _test_counter
    _test_counter += 1

    # Simulate different agent states based on counter
    states = ["idle", "working", "working", "working", "completed"]
    current_state = states[_test_counter % len(states)]
    
    # Simulate different actions
    actions = [
        "Analyzing codebase...",
        "Generating response... (245 tokens)",
        "Writing to file: src/utils.ts",
        "Using tool: git_commit",
        "Processing LLM response...",
        "Reading file: package.json",
        "Calling claude-sonnet-4-5...",
    ]
    current_action = actions[_test_counter % len(actions)] if current_state == "working" else ""
    
    # Simulate tools in progress
    tools = [None, None, "git_read_file", "git_write_file", "git_commit", None]
    tool_in_progress = tools[_test_counter % len(tools)] if current_state == "working" else None

    # Simulate streaming tokens (only when "working" and simulating streaming)
    streaming_tokens = None
    total_with_streaming = None
    if simulate_streaming and current_state == "working":
        streaming_tokens = random.randint(50, 300)
        total_with_streaming = (1500 * _test_counter) + streaming_tokens

    # Create mock telemetry data with all new fields
    mock_data = {
        "agent_name": agent_name,
        "status": current_state,
        "current_task": f"Implement feature #{_test_counter}" if current_state == "working" else "",
        "current_action": current_action,
        "test_counter": _test_counter,
        "process_metrics": {
            "pid": 12345,
            "cpu_percent": 15.5 + random.uniform(0, 30) if current_state == "working" else 2.0,
            "memory_mb": 256.0 + (_test_counter * 2) + random.uniform(0, 50),
            "threads": 8,
            "status": "running"
        },
        "token_usage": {
            "model": "claude-sonnet-4-5",
            "input_tokens": 1000 * _test_counter,
            "output_tokens": 500 * _test_counter,
            "total_tokens": 1500 * _test_counter,
            "streaming_tokens": streaming_tokens,
            "total_tokens_with_streaming": total_with_streaming
        },
        "files_read": ["src/index.ts", "package.json", "README.md"][:(_test_counter % 4)],
        "files_written": ["src/utils.ts", "src/api.ts"][:(_test_counter % 3)],
        "tool_calls": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "tool": "git_read_file",
                "arguments": {"path": "src/index.ts"},
                "result": "File content read successfully"
            }
        ] if _test_counter > 2 else [],
        "tool_in_progress": tool_in_progress,
        "git_activities": [
            {
                "operation": "commit",
                "branch": "feature/test",
                "message": f"Test commit #{_test_counter}",
                "files_changed": 3,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_name": agent_name
            }
        ] if _test_counter > 1 else [],
        "activity_logs": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": f"LLM call completed: +{500 + _test_counter * 100} tokens",
                "source": "llm",
                "agent_name": agent_name
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": current_action or f"Agent {agent_name} initialized",
                "source": "orchestrator",
                "agent_name": agent_name
            }
        ],
        "timestamp": datetime.utcnow().isoformat(),
        "heartbeat": True,
        "event_bus_connected": simulate_streaming  # True if simulating live streaming
    }

    # Broadcast via WebSocket
    await notify_agent_telemetry(
        agent_id=agent_name,
        team_id=team_id,
        event="metrics_update",
        data=mock_data
    )

    return {
        "status": "test_mode",
        "message": f"Mock telemetry #{_test_counter} sent via WebSocket for agent {agent_name}",
        "counter": _test_counter,
        "team_id": team_id,
        "simulate_streaming": simulate_streaming,
        "data": mock_data
    }
