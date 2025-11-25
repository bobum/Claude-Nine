from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


# Enums
class TeamStatus(str, Enum):
    active = "active"
    paused = "paused"
    stopped = "stopped"
    error = "error"


class AgentStatus(str, Enum):
    idle = "idle"
    working = "working"
    blocked = "blocked"
    error = "error"


class WorkItemStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    pr_ready = "pr_ready"
    completed = "completed"
    blocked = "blocked"
    cancelled = "cancelled"


class WorkItemSource(str, Enum):
    azure_devops = "azure_devops"
    jira = "jira"
    github = "github"
    linear = "linear"
    manual = "manual"


# Team schemas
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    product: str = Field(..., min_length=1, max_length=255)
    repo_path: str
    main_branch: str = "main"


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    product: Optional[str] = None
    repo_path: Optional[str] = None
    status: Optional[TeamStatus] = None


class Team(TeamBase):
    id: UUID4
    status: TeamStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Agent schemas
class AgentBase(BaseModel):
    name: str
    role: str
    goal: Optional[str] = None


class AgentCreate(AgentBase):
    team_id: UUID4


class Agent(AgentBase):
    id: UUID4
    team_id: UUID4
    status: AgentStatus
    worktree_path: Optional[str] = None
    current_branch: Optional[str] = None
    last_activity: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Work Item schemas
class WorkItemBase(BaseModel):
    external_id: str
    source: WorkItemSource
    title: str
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    priority: int = 0
    story_points: Optional[int] = None
    external_url: Optional[str] = None


class WorkItemCreate(WorkItemBase):
    team_id: Optional[UUID4] = None


class WorkItemUpdate(BaseModel):
    team_id: Optional[UUID4] = None
    status: Optional[WorkItemStatus] = None
    priority: Optional[int] = None


class WorkItem(WorkItemBase):
    id: UUID4
    team_id: Optional[UUID4] = None
    status: WorkItemStatus
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Team with agents
class TeamWithAgents(Team):
    agents: List[Agent] = []

    class Config:
        from_attributes = True


# Team with work queue
class TeamWithWorkQueue(Team):
    agents: List[Agent] = []
    work_items: List[WorkItem] = []

    class Config:
        from_attributes = True
