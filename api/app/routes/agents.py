from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..database import get_db
from ..models import Agent
from ..schemas import Agent as AgentSchema

router = APIRouter()


@router.get("/", response_model=List[AgentSchema])
def list_agents(
    skip: int = 0,
    limit: int = 100,
    team_id: UUID = None,
    db: Session = Depends(get_db)
):
    """List all agents, optionally filtered by team"""
    query = db.query(Agent)
    if team_id:
        query = query.filter(Agent.team_id == team_id)

    agents = query.offset(skip).limit(limit).all()
    return agents


@router.get("/{agent_id}", response_model=AgentSchema)
def get_agent(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Get agent by ID"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/status")
def get_agent_status(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Get detailed agent status"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": str(agent.id),
        "name": agent.name,
        "status": agent.status,
        "current_branch": agent.current_branch,
        "worktree_path": agent.worktree_path,
        "last_activity": agent.last_activity
    }


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete an agent"""
    db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.delete(db_agent)
    db.commit()
    return None
