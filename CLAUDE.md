# CLAUDE.md - Claude-Nine Development Guide

This document provides comprehensive guidance for Claude Code when working on the Claude-Nine multi-agent orchestration platform.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Development Patterns](#development-patterns)
5. [Status Enums](#status-enums)
6. [Configuration](#configuration)
7. [Common Commands](#common-commands)
8. [Key Abstractions](#key-abstractions)
9. [Testing Patterns](#testing-patterns)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

**Claude-Nine** is a multi-agent orchestration platform that enables multiple Claude AI agents to work simultaneously on different features in the same codebase—without stepping on each other's toes.

### Core Innovation

Uses **git worktrees** to give each agent its own isolated workspace:

```
my-project/
├── .git/                        # Shared git database
├── src/                         # Main directory (untouched)
└── .agent-workspace/
    ├── worktree-auth/           # Agent 1's private workspace
    ├── worktree-logging/        # Agent 2's private workspace
    └── worktree-docs/           # Agent 3's private workspace
```

### Key Benefits

- **True Parallelism**: Multiple agents work simultaneously (not sequentially)
- **No Conflicts**: Each agent has isolated working directory
- **Intelligent Merging**: Resolver Agent handles merge conflicts with LLM
- **100% Local**: Runs entirely on local machine, only needs Anthropic API
- **Real-time Monitoring**: Live telemetry via WebSocket to dashboard

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Dashboard (port 3001)                │
│                 Real-time monitoring & team management          │
└─────────────────────────────────────────────────────────────────┘
                                 │
                          WebSocket + REST
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (port 8000)                  │
│   Routes: /api/teams, /api/work-items, /api/runs, /api/telemetry│
│   Services: OrchestratorService, TelemetryService               │
│   Database: SQLite (default) or PostgreSQL                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                       Spawns subprocess per Run
                                 │
┌─────────────────────────────────────────────────────────────────┐
│              Multi-Agent Orchestrator (CrewAI)                  │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│   │ Agent 1 │  │ Agent 2 │  │ Agent 3 │  │ Agent N │  parallel │
│   │worktree │  │worktree │  │worktree │  │worktree │          │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
│                        ↓ merge phase ↓                         │
│                  ┌───────────────────┐                         │
│                  │  Resolver Agent   │ (on-demand conflicts)   │
│                  └───────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User creates Run** via Dashboard → POST /api/runs
2. **API spawns Orchestrator** subprocess with task definitions
3. **Orchestrator creates agents** with isolated git worktrees
4. **Agents work in parallel** using CrewAI with git tools
5. **Telemetry streams** to API via HTTP POST every 2 seconds
6. **API broadcasts** telemetry to Dashboard via WebSocket
7. **Post-completion merge** combines all feature branches
8. **Resolver Agent** handles any merge conflicts

### Workflow Loop

```
PRE-RUN CHECK → SESSION SETUP → PARALLEL WORK → POST-COMPLETION → PR READY
     │              │                │                │              │
     ▼              ▼                ▼                ▼              ▼
  Cleanup      Generate ID      N agents        Merge into      Integration
  orphaned     Create integ     spawn with      integration     branch ready
  worktrees    branch           worktrees       branch          for review
```

---

## File Structure

```
claude-9-demo/
├── api/                                    # FastAPI backend
│   ├── app/
│   │   ├── main.py                        # FastAPI app entry point
│   │   ├── config.py                      # Settings/env configuration
│   │   ├── database.py                    # SQLAlchemy setup
│   │   ├── models.py                      # ORM models (9,946 bytes)
│   │   ├── schemas.py                     # Pydantic schemas (5,631 bytes)
│   │   ├── websocket.py                   # WebSocket manager (4,469 bytes)
│   │   ├── personas.py                    # Agent personas
│   │   ├── routes/
│   │   │   ├── teams.py                   # Team CRUD + orchestrator control
│   │   │   ├── work_items.py              # Work item CRUD
│   │   │   ├── runs.py                    # Run creation and tracking
│   │   │   ├── telemetry.py               # Agent telemetry endpoints
│   │   │   ├── settings.py                # Config management
│   │   │   └── personas.py                # Persona listing
│   │   └── services/
│   │       ├── orchestrator_service.py    # Subprocess management (500+ lines)
│   │       └── telemetry_service.py       # Metric collection (1,700+ lines)
│   ├── requirements.txt
│   ├── .env                               # Environment variables
│   └── claude_nine.db                     # SQLite database
│
├── claude-multi-agent-orchestrator/        # CrewAI orchestrator
│   ├── orchestrator.py                    # Main orchestration (1,381 lines)
│   ├── simple_orchestrator.py             # Simplified version
│   ├── git_operations.py                  # Git worktree wrapper (931 lines)
│   ├── git_tools.py                       # CrewAI tool definitions (347 lines)
│   ├── telemetry_collector.py             # Telemetry collection (1,296 lines)
│   ├── tests/
│   │   ├── conftest.py                    # Pytest fixtures
│   │   ├── test_orchestrator.py
│   │   ├── test_git_operations.py
│   │   └── test_telemetry_collector.py
│   └── tasks/
│       └── example_tasks.yaml             # Example task definitions
│
├── dashboard/                              # Next.js frontend
│   ├── app/                               # App Router pages
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── settings/page.tsx
│   │   ├── teams/
│   │   │   ├── page.tsx
│   │   │   ├── new/page.tsx
│   │   │   └── [id]/page.tsx
│   │   └── work-items/page.tsx
│   ├── components/                        # React components
│   ├── lib/                               # Utilities, API clients
│   └── package.json
│
├── docs/                                   # Documentation
│   ├── local-setup-guide.md
│   ├── telemetry-architecture.md
│   ├── database-schema.md
│   ├── monitor-agent-architecture.md
│   └── bulk-assignment-guide.md
│
├── logs/                                   # Runtime logs
├── venv/                                   # Python 3.13 virtual environment
│
├── README.md                               # Project overview
├── GETTING_STARTED.md                      # Quick start guide
├── VISION.md                               # Project vision and roadmap
├── start.sh                                # Start all services
├── stop.sh                                 # Stop all services
└── activate.sh                             # Activate venv
```

---

## Development Patterns

### FastAPI Route Patterns

**Location**: `api/app/routes/`

#### Router Organization

Each route file creates a modular APIRouter:

```python
# api/app/routes/teams.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas

router = APIRouter()

@router.get("/", response_model=list[schemas.Team])
def list_teams(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return db.query(models.Team).offset(skip).limit(limit).all()
```

Routers are included in `main.py`:

```python
# api/app/main.py
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(work_items.router, prefix="/api/work-items", tags=["work-items"])
```

#### Standard CRUD Patterns

```python
# List with filters
@router.get("/", response_model=list[schemas.WorkItem])
def list_items(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    team_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.WorkItem)
    if status:
        query = query.filter(models.WorkItem.status == status)
    if team_id:
        query = query.filter(models.WorkItem.team_id == team_id)
    return query.offset(skip).limit(limit).all()

# Get by ID
@router.get("/{item_id}", response_model=schemas.WorkItem)
def get_item(item_id: UUID, db: Session = Depends(get_db)):
    item = db.query(models.WorkItem).filter(models.WorkItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# Create
@router.post("/", response_model=schemas.WorkItem, status_code=201)
def create_item(item: schemas.WorkItemCreate, db: Session = Depends(get_db)):
    db_item = models.WorkItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# Update (partial)
@router.put("/{item_id}", response_model=schemas.WorkItem)
def update_item(
    item_id: UUID,
    item: schemas.WorkItemUpdate,
    db: Session = Depends(get_db)
):
    db_item = db.query(models.WorkItem).filter(models.WorkItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item

# Delete
@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: UUID, db: Session = Depends(get_db)):
    db_item = db.query(models.WorkItem).filter(models.WorkItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
```

#### Dependency Injection

All routes use the `get_db` dependency for database sessions:

```python
# api/app/database.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Usage in routes
@router.get("/")
def list_items(db: Session = Depends(get_db)):
    ...
```

---

### SQLAlchemy Model Patterns

**Location**: `api/app/models.py`

#### Custom UUID Type (Cross-Database Compatibility)

```python
# api/app/models.py
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value
```

#### Timestamp Convention

Every model includes created_at and updated_at:

```python
from sqlalchemy import Column, DateTime, func

class Team(Base):
    __tablename__ = "teams"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    # ... other fields ...

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

#### Status Constraints

Uses CheckConstraints for status fields:

```python
from sqlalchemy import CheckConstraint

class Team(Base):
    __tablename__ = "teams"

    status = Column(String(50), default="active")

    __table_args__ = (
        CheckConstraint(
            status.in_(['active', 'paused', 'stopped', 'error']),
            name='team_status_check'
        ),
    )
```

#### Relationships with Cascades

```python
class Team(Base):
    __tablename__ = "teams"

    # One-to-many: delete children when parent deleted
    agents = relationship("Agent", back_populates="team", cascade="all, delete-orphan")
    work_items = relationship("WorkItem", back_populates="team", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="team", cascade="all, delete-orphan")

class Agent(Base):
    __tablename__ = "agents"

    team_id = Column(GUID(), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team = relationship("Team", back_populates="agents")
```

#### JSON Fields for Extensible Data

```python
from sqlalchemy import JSON

class WorkItem(Base):
    __tablename__ = "work_items"

    external_data = Column(JSON, nullable=True)  # Arbitrary external metadata

class RunTask(Base):
    __tablename__ = "run_tasks"

    telemetry_data = Column(JSON, nullable=True)  # Live telemetry snapshots
```

---

### Pydantic Schema Patterns

**Location**: `api/app/schemas.py`

#### Schema Hierarchy

```python
# Base - fields without IDs (for input validation)
class WorkItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    source: str = "manual"
    external_id: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)

# Create - for POST requests
class WorkItemCreate(WorkItemBase):
    team_id: UUID
    # May add extra fields needed only at creation

# Update - all fields Optional for PATCH semantics
class WorkItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[WorkItemStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=5)

# Full - includes ID, timestamps, status (from database)
class WorkItem(WorkItemBase):
    id: UUID
    team_id: UUID
    status: WorkItemStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode
```

#### Status Enums

```python
from enum import Enum

class TeamStatus(str, Enum):
    active = "active"
    paused = "paused"
    stopped = "stopped"
    error = "error"

class WorkItemStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    pr_ready = "pr_ready"
    completed = "completed"
    blocked = "blocked"
    cancelled = "cancelled"

class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    merging = "merging"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
```

#### Nested Schemas

```python
class TeamWithAgents(Team):
    agents: list[Agent] = []

class TeamWithWorkQueue(Team):
    agents: list[Agent] = []
    work_items: list[WorkItem] = []

class RunWithTasks(Run):
    tasks: list[RunTask] = []
```

---

### CrewAI Agent/Task Patterns

**Location**: `claude-multi-agent-orchestrator/`

#### Agent Creation Pattern

```python
# orchestrator.py
def create_feature_agent(self, feature_config: dict) -> tuple[Agent, str]:
    """Create agent with isolated worktree."""

    branch_name = feature_config["branch"]
    worktree_path = self.git_ops.create_worktree(
        branch_name=branch_name,
        worktree_path=f".agent-workspace/worktree-{branch_name}",
        main_branch=self.config.get("main_branch", "main")
    )

    # Create tools scoped to this worktree
    tools = [
        CreateBranchTool(repo_path=worktree_path),
        CommitChangesTool(repo_path=worktree_path),
        WriteFileTool(repo_path=worktree_path),
        ReadFileTool(repo_path=worktree_path),
    ]

    agent = Agent(
        role=feature_config["role"],
        goal=feature_config["goal"],
        backstory=feature_config.get("backstory", ""),
        tools=tools,
        llm=self.llm,
        verbose=True
    )

    return agent, worktree_path
```

#### Task Creation Pattern

```python
def create_feature_task(self, agent: Agent, feature_config: dict, worktree_path: str) -> Task:
    """Create task for agent."""

    return Task(
        description=feature_config["description"],
        expected_output=feature_config["expected_output"],
        agent=agent,
        async_execution=True  # Enable parallel execution
    )
```

#### Crew Execution

```python
def run(self):
    """Execute all agents in parallel."""

    agents = []
    tasks = []

    for feature in self.tasks["features"]:
        agent, worktree_path = self.create_feature_agent(feature)
        task = self.create_feature_task(agent, feature, worktree_path)
        agents.append(agent)
        tasks.append(task)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.parallel,  # or Process.sequential
        verbose=True
    )

    result = crew.kickoff()

    # Post-completion: merge all branches
    self.merge_all_branches()
```

#### Git Tool Pattern

```python
# git_tools.py
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class WriteFileInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")

class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = "Write content to a file in the repository"
    args_schema: type[BaseModel] = WriteFileInput

    def __init__(self, repo_path: str):
        super().__init__()
        self.repo_path = repo_path
        self.git_ops = GitOperations(repo_path)

    def _run(self, file_path: str, content: str) -> str:
        try:
            self.git_ops.write_file_content(file_path, content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"
```

---

### WebSocket Patterns

**Location**: `api/app/websocket.py`

#### Connection Manager

```python
from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.team_subscribers: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # Remove from all team subscriptions
        for team_id in list(self.team_subscribers.keys()):
            if websocket in self.team_subscribers[team_id]:
                self.team_subscribers[team_id].remove(websocket)

    async def subscribe_to_team(self, websocket: WebSocket, team_id: str):
        if team_id not in self.team_subscribers:
            self.team_subscribers[team_id] = []
        if websocket not in self.team_subscribers[team_id]:
            self.team_subscribers[team_id].append(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

    async def send_to_team(self, team_id: str, message: dict):
        if team_id in self.team_subscribers:
            for connection in self.team_subscribers[team_id]:
                await connection.send_json(message)

manager = ConnectionManager()
```

#### WebSocket Endpoint

```python
# api/app/main.py
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "subscribe_team":
                team_id = data.get("team_id")
                await manager.subscribe_to_team(websocket, team_id)
                await websocket.send_json({
                    "type": "subscribed",
                    "team_id": team_id
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

#### Notification Functions

```python
# api/app/websocket.py
import time

async def notify_team_update(team_id: str, event: str, data: dict):
    await manager.send_to_team(team_id, {
        "type": "team_update",
        "team_id": team_id,
        "event": event,
        "data": data,
        "timestamp": time.time()
    })

async def notify_agent_telemetry(team_id: str, agent_name: str, telemetry: dict):
    await manager.send_to_team(team_id, {
        "type": "agent_telemetry",
        "team_id": team_id,
        "agent_name": agent_name,
        "data": telemetry,
        "timestamp": time.time()
    })
```

---

### Telemetry Patterns

**Location**: `claude-multi-agent-orchestrator/telemetry_collector.py`

#### Data Classes

```python
from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime

@dataclass
class ProcessMetrics:
    pid: int
    cpu_percent: float
    memory_mb: float
    threads: int
    status: str

@dataclass
class TokenUsage:
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float

@dataclass
class GitActivity:
    operation: str  # commit, checkout, merge, etc.
    branch: str
    message: Optional[str] = None
    files_changed: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ActivityLog:
    timestamp: datetime
    level: str  # INFO, WARN, ERROR
    message: str
    source: str
    agent_name: str
```

#### Telemetry Collector

```python
class TelemetryCollector:
    def __init__(self, api_url: str, team_id: str, agent_name: str):
        self.api_url = api_url
        self.team_id = team_id
        self.agent_name = agent_name
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._collection_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _collection_loop(self):
        while self.running:
            metrics = self._collect_metrics()
            self._send_telemetry(metrics)
            time.sleep(2)  # Send every 2 seconds

    def _collect_metrics(self) -> dict:
        import psutil
        process = psutil.Process()

        return {
            "process_metrics": {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "threads": process.num_threads(),
                "status": process.status()
            },
            "token_usage": self.current_token_usage,
            "git_activity": self.recent_git_activity,
            "activity_logs": self.recent_logs
        }

    def _send_telemetry(self, metrics: dict):
        try:
            requests.post(
                f"{self.api_url}/api/telemetry/agent/{self.agent_name}",
                json=metrics,
                headers={"X-Team-ID": self.team_id}
            )
        except Exception as e:
            print(f"Failed to send telemetry: {e}")
```

#### CrewAI Event Bus Integration

```python
# For live token streaming
from crewai.utilities.events import (
    LLMStreamChunkEvent,
    LLMCallStartedEvent,
    LLMCallCompletedEvent
)

def setup_event_handlers(collector: TelemetryCollector):
    @crewai_event_bus.on(LLMStreamChunkEvent)
    def on_stream_chunk(event: LLMStreamChunkEvent):
        # Live token updates
        collector.update_streaming_tokens(event.chunk)

    @crewai_event_bus.on(LLMCallCompletedEvent)
    def on_llm_complete(event: LLMCallCompletedEvent):
        collector.finalize_token_usage(
            input_tokens=event.input_tokens,
            output_tokens=event.output_tokens
        )
```

---

## Status Enums

### Team Status

| Status | Description |
|--------|-------------|
| `active` | Team is ready to accept work |
| `paused` | Team is temporarily paused |
| `stopped` | Team is stopped |
| `error` | Team encountered an error |

### Agent Status

| Status | Description |
|--------|-------------|
| `idle` | Agent is waiting for work |
| `working` | Agent is executing a task |
| `blocked` | Agent is blocked on something |
| `error` | Agent encountered an error |

### Work Item Status

| Status | Description |
|--------|-------------|
| `queued` | Work item is in queue |
| `in_progress` | Work item is being worked on |
| `pr_ready` | Work is done, PR ready |
| `completed` | Work item fully completed |
| `blocked` | Work item is blocked |
| `cancelled` | Work item was cancelled |

### Run Status

| Status | Description |
|--------|-------------|
| `pending` | Run is created but not started |
| `running` | Orchestrator is executing |
| `merging` | Post-completion merge phase |
| `completed` | Run finished successfully |
| `failed` | Run failed |
| `cancelled` | Run was cancelled |

### RunTask Status

| Status | Description |
|--------|-------------|
| `pending` | Task not started |
| `running` | Task is executing |
| `completed` | Task finished successfully |
| `failed` | Task failed |
| `retrying` | Task is being retried |

---

## Configuration

### Environment Variables

**Location**: `api/.env`

```bash
# Database
DATABASE_URL=sqlite:///./claude_nine.db
# For PostgreSQL: postgresql://user:pass@localhost:5432/claude_nine

# API Server
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Orchestrator
FORCE_DRY_RUN=False  # Force mock mode (no API credits)

# Security
SECRET_KEY=your-secret-key

# External APIs
ANTHROPIC_API_KEY=sk-ant-...
ADO_PAT=  # Azure DevOps Personal Access Token (optional)
```

### Settings Class

```python
# api/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = "sqlite:///./claude_nine.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    force_dry_run: bool = False
    secret_key: str = "change-me"
    anthropic_api_key: str = ""
    ado_pat: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()
```

### Task YAML Format

```yaml
# claude-multi-agent-orchestrator/tasks/example_tasks.yaml
features:
  - name: user-authentication
    branch: feature/user-auth
    work_item_id: "550e8400-e29b-41d4-a716-446655440001"
    external_id: "TASK-123"
    role: "Senior Software Developer"
    goal: "Implement user authentication with JWT tokens"
    description: |
      Implement a complete user authentication system:
      1. Create login/logout endpoints
      2. Implement JWT token generation
      3. Add password hashing
      4. Create auth middleware

      Acceptance Criteria:
      - Users can register and login
      - Tokens expire after 24 hours
      - Passwords are securely hashed
    expected_output: "Complete authentication implementation with tests"

  - name: user-registration
    branch: feature/user-registration
    # ... additional features
```

---

## Common Commands

### Start Services

```bash
# Start everything (API + Dashboard)
./start.sh

# Or manually:
# Terminal 1 - API
cd api
source ../venv/bin/activate  # or: . ../venv/Scripts/activate (Windows)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Dashboard
cd dashboard
npm run dev
```

### Stop Services

```bash
# Stop everything
./stop.sh

# Or manually kill processes on ports 8000 and 3001
```

### Database Operations

```bash
# Reset database (drop and recreate tables)
cd api
python reset_db.py

# Reset and seed with test data
python reset_and_seed.py

# Just seed (add test data)
python seed_test_data.py
```

### Run Tests

```bash
# Orchestrator tests
cd claude-multi-agent-orchestrator
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Run Orchestrator Manually

```bash
cd claude-multi-agent-orchestrator

# Normal mode (uses API credits)
python orchestrator.py --config config.yaml --tasks tasks/example_tasks.yaml

# Dry-run mode (mock LLM, no API credits)
python orchestrator.py --config config.yaml --tasks tasks/example_tasks.yaml --dry-run

# Cleanup only (remove orphaned worktrees)
python orchestrator.py --cleanup-only
```

### Check Health

```bash
# API health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Dashboard (browser)
open http://localhost:3001
```

---

## Key Abstractions

### Git Worktrees

Git worktrees allow multiple working directories from the same repository:

```bash
# How it works internally:
git worktree add .agent-workspace/worktree-feature-auth feature/auth

# Results in:
my-repo/
├── .git/                    # Shared database
├── src/                     # Main working directory
└── .agent-workspace/
    └── worktree-feature-auth/   # Agent's isolated copy
        ├── src/                 # Independent file copies
        └── .git -> ../../.git   # Linked to main .git
```

**Benefits**:
- Shared `.git` database (efficient)
- Independent file copies (isolated)
- Each worktree can be on different branch
- Changes don't affect other worktrees

**Cleanup**:
```bash
git worktree remove .agent-workspace/worktree-feature-auth
git worktree prune  # Clean up stale references
```

### Transitory Agents

Agents are **not persistent**—they're created per work item and cleaned up after completion:

1. **Creation**: When a Run starts, agents are created for each work item
2. **Execution**: Agents work in parallel in isolated worktrees
3. **Cleanup**: When Run completes, worktrees are removed

This enables:
- Dynamic scaling (create only what's needed)
- Clean state between runs
- No persistent agent management

### Subprocess Orchestration

The orchestrator runs as a **separate Python subprocess**:

```python
# api/app/services/orchestrator_service.py
def start_team(team_id: UUID, db: Session):
    process = subprocess.Popen(
        [
            sys.executable,
            "orchestrator.py",
            "--config", config_path,
            "--tasks", tasks_path,
            "--team-id", str(team_id)
        ],
        cwd=team.repo_path,
        env={
            **os.environ,
            "ANTHROPIC_API_KEY": settings.anthropic_api_key,
            "CLAUDE_NINE_API_URL": f"http://localhost:{settings.api_port}"
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Monitor in background thread
    threading.Thread(
        target=_monitor_orchestrator,
        args=(team_id, process, db)
    ).start()
```

**Why subprocess**:
- Isolation from API process
- Can be killed independently
- Memory isolation
- Allows parallel team execution

**PID Tracking** (for cleanup):
- PIDs are written to `logs/orchestrator.pids` when processes start
- Format: `PID:team_id` per line
- `./stop.sh` kills all tracked processes
- On API startup, stale processes are automatically detected and killed
- **IMPORTANT**: Always use `./stop.sh` when debugging to avoid zombie processes!

### Integration Branch

All feature branches merge into an integration branch:

```
main
  └── integration/abc123 (integration branch for this run)
        ├── feature/auth (Agent 1's work)
        ├── feature/logging (Agent 2's work)
        └── feature/docs (Agent 3's work)
```

**Flow**:
1. Integration branch created from main at run start
2. Each agent works on feature branch from main
3. Post-completion: all feature branches merge into integration
4. Resolver agent handles any conflicts
5. Integration branch ready for PR to main

---

## Testing Patterns

### Pytest Fixtures

**Location**: `claude-multi-agent-orchestrator/tests/conftest.py`

```python
import pytest
from pathlib import Path
import tempfile
import shutil
from git import Repo

@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    repo = Repo.init(temp_dir)

    # Configure git user
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Create initial commit
    readme = Path(temp_dir) / "README.md"
    readme.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def temp_git_repo_with_remote(temp_git_repo):
    """Create repo with a bare remote for push testing."""
    remote_dir = tempfile.mkdtemp()
    bare_repo = Repo.init(remote_dir, bare=True)

    repo = Repo(temp_git_repo)
    repo.create_remote("origin", remote_dir)
    repo.remotes.origin.push("main")

    yield temp_git_repo, remote_dir

    shutil.rmtree(remote_dir, ignore_errors=True)

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
```

### Mocking Patterns

```python
from unittest.mock import Mock, MagicMock, patch

def test_orchestrator_with_mock_llm():
    with patch("orchestrator.ChatAnthropic") as mock_llm:
        mock_llm.return_value = MagicMock()

        orchestrator = MultiAgentOrchestrator(
            config_path="test_config.yaml",
            dry_run=True
        )

        result = orchestrator.run()

        assert result.success
        mock_llm.assert_called_once()

def test_telemetry_posting():
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200

        collector = TelemetryCollector(
            api_url="http://localhost:8000",
            team_id="test-team",
            agent_name="test-agent"
        )

        collector._send_telemetry({"test": "data"})

        mock_post.assert_called_once()
        assert "telemetry" in mock_post.call_args[0][0]
```

### Path Handling

Always use `pathlib.Path` for cross-platform compatibility:

```python
from pathlib import Path

def test_file_operations(temp_git_repo):
    repo_path = Path(temp_git_repo)
    test_file = repo_path / "src" / "test.py"

    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("print('hello')")

    assert test_file.exists()
    assert test_file.read_text() == "print('hello')"
```

---

## Troubleshooting

### Common Issues

#### "Worktree already exists"

**Cause**: Previous run didn't clean up properly.

**Solution**:
```bash
cd your-repo
git worktree list
git worktree remove .agent-workspace/worktree-name --force
git worktree prune
# Or run cleanup-only mode:
python orchestrator.py --cleanup-only
```

#### Stale Orchestrator Processes (IMPORTANT for Debugging)

**Cause**: The API was restarted (e.g., during debugging) but orchestrator subprocesses kept running with OLD code.

**Symptoms**:
- Multiple orchestrator processes running
- Changes to orchestrator code not taking effect
- Unexpected behavior after restarting the API
- High CPU/memory usage from zombie processes

**Solution**:
```bash
# ALWAYS use stop.sh to stop Claude-Nine
./stop.sh

# This kills:
# 1. Orchestrator subprocesses (from logs/orchestrator.pids)
# 2. API server (uvicorn)
# 3. Dashboard (Next.js)
```

**Prevention**:
- **Always run `./stop.sh` before restarting** during development/debugging
- Don't just stop the API - orchestrator subprocesses will keep running!
- The API automatically cleans up stale processes on startup, but it's better to stop them explicitly

**How PID Tracking Works**:
- When an orchestrator subprocess starts, its PID is written to `logs/orchestrator.pids`
- Format: `PID:team_id` (one per line)
- `stop.sh` reads this file and kills all listed processes
- PIDs are removed when processes complete or are stopped via API

**Manual Cleanup** (if needed):
```bash
# Check for running orchestrator processes
cat logs/orchestrator.pids
ps aux | grep orchestrator.py

# Kill manually if needed
kill <PID>

# Clear the PID file
> logs/orchestrator.pids
```

#### "API key not found"

**Cause**: ANTHROPIC_API_KEY not set.

**Solution**:
```bash
# Check environment
echo $ANTHROPIC_API_KEY

# Set in .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> api/.env

# Or export directly
export ANTHROPIC_API_KEY=sk-ant-...
```

#### "Not in a git repository"

**Cause**: Orchestrator started from wrong directory.

**Solution**:
```bash
# Ensure you're in the target repo
cd /path/to/target/repo
git status  # Should work

# Run orchestrator from repo root
python /path/to/orchestrator.py --config config.yaml --tasks tasks.yaml
```

#### "Database is locked"

**Cause**: SQLite concurrent access issue.

**Solution**:
```bash
# Stop all processes
./stop.sh

# Remove lock file if exists
rm -f api/claude_nine.db-journal

# Restart
./start.sh
```

#### "Port already in use"

**Cause**: Previous process didn't shut down.

**Solution**:
```bash
# Find process using port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>

# Or use stop script
./stop.sh
```

#### "WebSocket connection failed"

**Cause**: API not running or CORS issue.

**Solution**:
1. Ensure API is running: `curl http://localhost:8000/health`
2. Check CORS settings in `api/app/main.py`
3. Verify dashboard is using correct API URL

#### "Mock telemetry showing 66666 tokens"

**Cause**: Running in dry-run mode.

**Solution**: This is expected behavior in dry-run mode. The alternating 66666/0 tokens indicate mock mode is active. To use real API:
```bash
# Remove --dry-run flag
python orchestrator.py --config config.yaml --tasks tasks.yaml

# Or set in .env
FORCE_DRY_RUN=False
```

### Log Locations

| Component | Log Location |
|-----------|--------------|
| API | `logs/api.log` or stdout |
| Dashboard | `logs/dashboard.log` or stdout |
| Orchestrator | `.agent-workspace/orchestrator.log` |
| Telemetry | `.agent-workspace/telemetry/*.json` |

### Debug Mode

Enable debug mode for verbose logging:

```bash
# API
DEBUG=True uvicorn app.main:app --reload

# Orchestrator
python orchestrator.py --config config.yaml --tasks tasks.yaml --verbose
```

---

## Quick Reference

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/health/db` | Database health |
| GET | `/api/teams` | List teams |
| POST | `/api/teams` | Create team |
| GET | `/api/teams/{id}` | Get team |
| POST | `/api/runs` | Start orchestrator run |
| GET | `/api/runs/{id}` | Get run status |
| POST | `/api/telemetry/agent/{name}` | Receive telemetry |
| WS | `/ws` | WebSocket for real-time updates |

### Key Files to Know

| File | Purpose |
|------|---------|
| `api/app/main.py` | FastAPI entry point |
| `api/app/models.py` | Database models |
| `api/app/schemas.py` | Pydantic schemas |
| `api/app/services/orchestrator_service.py` | Subprocess management |
| `claude-multi-agent-orchestrator/orchestrator.py` | Main orchestration |
| `claude-multi-agent-orchestrator/git_operations.py` | Git wrapper |
| `claude-multi-agent-orchestrator/git_tools.py` | CrewAI tools |
| `claude-multi-agent-orchestrator/telemetry_collector.py` | Telemetry |

### Pricing (Claude Sonnet 4.5)

```
Input tokens:  $3.00 per million
Output tokens: $15.00 per million
```

---

*Last updated: December 2024*
*Branch: feature/enhanced-telemetry-live-tokens*
