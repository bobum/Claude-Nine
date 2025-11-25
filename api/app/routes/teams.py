from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..database import get_db
from ..models import Team, Agent
from ..schemas import (
    Team as TeamSchema,
    TeamCreate,
    TeamUpdate,
    TeamWithAgents,
    TeamWithWorkQueue,
    AgentCreate,
    Agent as AgentSchema
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
def start_team(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Start a team"""
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    db_team.status = "active"
    db.commit()

    # TODO: Actually start the orchestrator for this team

    return {"message": "Team started", "team_id": str(team_id)}


@router.post("/{team_id}/stop")
def stop_team(
    team_id: UUID,
    db: Session = Depends(get_db)
):
    """Stop a team"""
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    db_team.status = "stopped"
    db.commit()

    # TODO: Actually stop the orchestrator for this team

    return {"message": "Team stopped", "team_id": str(team_id)}


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


@router.post("/{team_id}/agents", response_model=AgentSchema, status_code=status.HTTP_201_CREATED)
def add_agent_to_team(
    team_id: UUID,
    agent: AgentCreate,
    db: Session = Depends(get_db)
):
    """Add an agent to a team"""
    # Verify team exists
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if agent name already exists in team
    existing = db.query(Agent).filter(
        Agent.team_id == team_id,
        Agent.name == agent.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent name already exists in this team")

    db_agent = Agent(team_id=team_id, **agent.dict(exclude={'team_id'}))
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent
