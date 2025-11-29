from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..database import get_db
from ..models import Team
from ..schemas import (
    Team as TeamSchema,
    TeamCreate,
    TeamUpdate,
    TeamWithAgents,
    TeamWithWorkQueue,
)

router = APIRouter()


@router.get("/", response_model=List[TeamSchema])
def list_teams(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all teams"""
    teams = db.query(Team).offset(skip).limit(limit).all()
    return teams


@router.get("/{team_id}", response_model=TeamWithAgents)
def get_team(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Get team by ID with agents"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/{team_id}/full", response_model=TeamWithWorkQueue)
def get_team_full(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Get team by ID with agents and work queue"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/", response_model=TeamSchema, status_code=status.HTTP_201_CREATED)
def create_team(
    team: TeamCreate,
    db: Session = Depends(get_db)
):
    """Create a new team"""
    # Check if team name already exists
    existing = db.query(Team).filter(Team.name == team.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team name already exists")

    db_team = Team(**team.dict())
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team


@router.put("/{team_id}", response_model=TeamSchema)
def update_team(
    team_id: UUID,
    team_update: TeamUpdate,
    db: Session = Depends(get_db)
):
    """Update a team"""
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Update only provided fields
    for field, value in team_update.dict(exclude_unset=True).items():
        setattr(db_team, field, value)

    db.commit()
    db.refresh(db_team)
    return db_team


@router.get("/{team_id}/readiness")
def get_team_readiness(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Check if team is ready to start and return detailed status"""
    from ..models import WorkItem
    import os

    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check all prerequisites
    checks = {
        "has_repository": bool(db_team.repo_path),
        "repository_exists": False,
        "is_git_repository": False,
        "has_queued_work": False
    }

    issues = []

    # Check repository
    if checks["has_repository"]:
        if os.path.exists(db_team.repo_path):
            checks["repository_exists"] = True
            git_dir = os.path.join(db_team.repo_path, ".git")
            if os.path.exists(git_dir):
                checks["is_git_repository"] = True
            else:
                issues.append(f"'{db_team.repo_path}' is not a git repository")
        else:
            issues.append(f"Repository path '{db_team.repo_path}' does not exist")
    else:
        issues.append("No repository path configured")

    # Check work items
    queued_items = db.query(WorkItem).filter(
        WorkItem.team_id == team_id,
        WorkItem.status == "queued"
    ).all()

    checks["has_queued_work"] = len(queued_items) > 0
    if not checks["has_queued_work"]:
        issues.append("No work items in queue")

    # Determine overall readiness
    is_ready = all(checks.values())

    return {
        "team_id": str(team_id),
        "is_ready": is_ready,
        "checks": checks,
        "issues": issues,
        "queued_work_count": len(queued_items),
        "queued_work_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "status": item.status,
                "priority": item.priority
            }
            for item in queued_items
        ]
    }


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a team"""
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    db.delete(db_team)
    db.commit()
    return None


@router.post("/{team_id}/start")
async def start_team(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Start a team (TEST MODE: sends mock telemetry instead of running orchestrator)"""
    from datetime import datetime
    from ..websocket import notify_agent_telemetry
    import asyncio
    import random
    
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check for queued work items
    from ..models import WorkItem
    queued_items = db.query(WorkItem).filter(
        WorkItem.team_id == team_id,
        WorkItem.status == "queued"
    ).all()

    if not queued_items:
        raise HTTPException(
            status_code=400,
            detail="Cannot start team: No work items in queue. Please assign work items before starting."
        )

    # Validate repository path exists
    import os
    if not db_team.repo_path or not os.path.exists(db_team.repo_path):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start team: Repository path '{db_team.repo_path}' does not exist or is not accessible"
        )

    # Check if it's a git repository
    git_dir = os.path.join(db_team.repo_path, ".git")
    if not os.path.exists(git_dir):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start team: '{db_team.repo_path}' is not a git repository"
        )

    db_team.status = "active"
    db.commit()

    # Start the real orchestrator
    from ..services.orchestrator_service import get_orchestrator_service
    orch_service = get_orchestrator_service()
    result = orch_service.start_team(team_id, db)

    return {
        "message": "Team started successfully",
        "team_id": str(team_id),
        "queued_work_count": len(queued_items),
        "orchestrator_status": result.get("status", "unknown"),
        "status": "active"
    }


@router.post("/{team_id}/stop")
def stop_team(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Stop a team"""
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Stop the orchestrator service
    from ..services.orchestrator_service import get_orchestrator_service
    orch_service = get_orchestrator_service()

    result = orch_service.stop_team(team_id, db)

    db_team.status = "stopped"
    db.commit()

    return {
        "message": "Team stopped",
        "team_id": str(team_id),
        "orchestrator_status": result["status"]
    }


@router.get("/{team_id}/orchestrator-status")
def get_orchestrator_status(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Get the status of the orchestrator for this team"""
    from ..services.orchestrator_service import get_orchestrator_service
    orch_service = get_orchestrator_service()

    status = orch_service.get_status(team_id)
    return status


@router.post("/{team_id}/pause")
def pause_team(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Pause a team"""
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    db_team.status = "paused"
    db.commit()

    # TODO: Actually pause the orchestrator for this team

    return {"message": "Team paused", "team_id": str(team_id)}
