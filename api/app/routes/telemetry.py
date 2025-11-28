"""Telemetry endpoints for agent monitoring."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
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
    cost_usd: float


class ActivityLog(BaseModel):
    """Activity log entry"""
    timestamp: str
    level: str
    message: str
    source: str
    agent_name: Optional[str] = None


class AgentTelemetryData(BaseModel):
    """Agent telemetry data from orchestrator"""
    team_id: str
    agent_name: str
    process_metrics: ProcessMetrics
    token_usage: TokenUsage
    git_activities: List[GitActivity]
    activity_logs: List[ActivityLog]
    timestamp: str


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
    """
    try:
        # Broadcast telemetry to WebSocket clients
        await notify_agent_telemetry(
            agent_id=agent_name,  # Using agent_name as agent_id for now
            team_id=data.team_id,
            event="metrics_update",
            data={
                "agent_name": agent_name,
                "process_metrics": data.process_metrics.dict(),
                "token_usage": data.token_usage.dict(),
                "git_activities": [activity.dict() for activity in data.git_activities],
                "activity_logs": [log.dict() for log in data.activity_logs],
                "timestamp": data.timestamp
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
    team_id: str = "f398aeda-5257-45ec-a09f-b02d0de402ae"
):
    """
    TEMPORARY TEST MODE: Sends mock telemetry via WebSocket to test the connection.

    This allows testing WebSocket delivery without running the full orchestrator.
    Call this endpoint (e.g., http://localhost:8000/api/telemetry/agent/DevAgent)
    and watch the dashboard to see if the mock data appears in the agent card.

    TODO: Replace with actual cached telemetry data retrieval in production.
    """
    global _test_counter
    _test_counter += 1

    # Create mock telemetry data
    mock_data = {
        "agent_name": agent_name,
        "test_counter": _test_counter,
        "process_metrics": {
            "pid": 12345,
            "cpu_percent": 15.5 + (_test_counter % 10),
            "memory_mb": 256.0 + (_test_counter * 2),
            "threads": 8,
            "status": "running"
        },
        "token_usage": {
            "model": "claude-sonnet-4-5",
            "input_tokens": 1000 * _test_counter,
            "output_tokens": 500 * _test_counter,
            "total_tokens": 1500 * _test_counter,
            "cost_usd": 0.01 * _test_counter
        },
        "git_activities": [
            {
                "operation": "commit",
                "branch": "feature/test",
                "message": f"Test commit #{_test_counter}",
                "files_changed": 3,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_name": agent_name
            }
        ],
        "activity_logs": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": f"Test activity log entry #{_test_counter}",
                "source": "test_endpoint",
                "agent_name": agent_name
            }
        ],
        "timestamp": datetime.utcnow().isoformat()
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
        "data": mock_data
    }
