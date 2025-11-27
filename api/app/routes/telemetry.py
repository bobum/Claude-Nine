"""Telemetry endpoints for agent monitoring."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

from ..websocket import notify_agent_telemetry

router = APIRouter()


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
async def get_agent_telemetry(agent_name: str):
    """
    Get current telemetry data for a specific agent.

    Note: This is a placeholder for future implementation where we might
    cache telemetry data in memory or database.
    """
    return {
        "status": "not_implemented",
        "message": "Telemetry data is currently only available via WebSocket",
        "agent_name": agent_name
    }
