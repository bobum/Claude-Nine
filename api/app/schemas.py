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


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    merging = "merging"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunTaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"


# Team schemas
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    product: str = Field(..., min_length=1, max_length=255)
    repo_path: str
    main_branch: str = "main"
    max_concurrent_tasks: int = 4  # 0 = unlimited


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    product: Optional[str] = None
    repo_path: Optional[str] = None
    max_concurrent_tasks: Optional[int] = None
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
    persona_type: str = "dev"  # dev, monitor, orchestrator
    specialization: Optional[str] = None
    role: str
    goal: Optional[str] = None


class AgentCreate(AgentBase):
    pass


class Agent(AgentBase):
    id: UUID4
    team_id: UUID4
    persona_type: str
    specialization: Optional[str] = None
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
    # Completion results
    branch_name: Optional[str] = None
    commits_count: Optional[int] = None
    files_changed_count: Optional[int] = None
    pr_url: Optional[str] = None


class BulkAssignRequest(BaseModel):
    work_item_ids: List[UUID4]
    team_id: UUID4


class WorkItem(WorkItemBase):
    id: UUID4
    team_id: Optional[UUID4] = None
    status: WorkItemStatus
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Completion results
    branch_name: Optional[str] = None
    commits_count: Optional[int] = None
    files_changed_count: Optional[int] = None
    pr_url: Optional[str] = None

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

# Run schemas (orchestrator session tracking)
class RunBase(BaseModel):
    session_id: str


class RunCreate(RunBase):
    team_id: UUID4
    selected_work_item_ids: List[UUID4] = []
    dry_run: bool = False  # Default to live mode (force_dry_run in config can override)


class RunTaskBase(BaseModel):
    work_item_id: Optional[UUID4] = None
    agent_name: Optional[str] = None


class RunTask(RunTaskBase):
    id: UUID4
    run_id: UUID4
    branch_name: Optional[str] = None
    worktree_path: Optional[str] = None
    status: RunTaskStatus
    telemetry_data: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    work_item: Optional[WorkItem] = None

    class Config:
        from_attributes = True


class Run(RunBase):
    id: UUID4
    team_id: UUID4
    status: RunStatus
    integration_branch: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tasks: List[RunTask] = []

    class Config:
        from_attributes = True


class RunWithTasks(Run):
    tasks: List[RunTask] = []

    class Config:
        from_attributes = True


# Team with runs
class TeamWithRuns(Team):
    runs: List[Run] = []

    class Config:
        from_attributes = True
