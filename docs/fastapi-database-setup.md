# FastAPI Database Connection Setup

## Overview

This guide shows how to set up database connections in FastAPI using SQLAlchemy with PostgreSQL.

## Project Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── config.py            # Configuration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── teams.py
│   │   ├── agents.py
│   │   └── work_items.py
│   └── services/
│       └── __init__.py
├── alembic/                 # Database migrations
├── requirements.txt
└── .env
```

## 1. Requirements

Create `api/requirements.txt`:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pydantic-settings==2.1.0
python-dotenv==1.0.0
asyncpg==0.29.0
```

Install:

```bash
cd api
pip install -r requirements.txt
```

## 2. Environment Configuration

Create `api/.env`:

```bash
# Database
DATABASE_URL=postgresql://claude_admin:YourPassword@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Security
SECRET_KEY=your-secret-key-here-change-in-production

# External APIs
ANTHROPIC_API_KEY=your-anthropic-key
ADO_PAT=your-azure-devops-pat
```

Create `api/app/config.py`:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Security
    secret_key: str

    # External APIs
    anthropic_api_key: str = ""
    ado_pat: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

## 3. Database Connection

Create `api/app/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,        # Connection pool size
    max_overflow=20,     # Max overflow connections
    echo=settings.debug  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    """
    Dependency that provides a database session.
    Automatically closes session after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## 4. SQLAlchemy Models

Create `api/app/models.py`:

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .database import Base

class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    product = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    main_branch = Column(String(100), default="main")
    status = Column(String(50), nullable=False, default="stopped")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    agents = relationship("Agent", back_populates="team", cascade="all, delete-orphan")
    work_items = relationship("WorkItem", back_populates="team")
    integrations = relationship("Integration", back_populates="team", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="team", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(status.in_(['active', 'paused', 'stopped', 'error']), name='teams_status_check'),
    )

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    goal = Column(Text)
    worktree_path = Column(String(500))
    current_branch = Column(String(255))
    status = Column(String(50), nullable=False, default="idle")
    last_activity = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team = relationship("Team", back_populates="agents")
    activity_logs = relationship("ActivityLog", back_populates="agent", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(status.in_(['idle', 'working', 'blocked', 'error']), name='agents_status_check'),
    )

class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"))
    external_id = Column(String(255), nullable=False)
    source = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    acceptance_criteria = Column(Text)
    status = Column(String(50), nullable=False, default="queued")
    priority = Column(Integer, default=0)
    story_points = Column(Integer)
    external_url = Column(String(500))
    external_data = Column(JSONB)
    assigned_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team = relationship("Team", back_populates="work_items")
    activity_logs = relationship("ActivityLog", back_populates="work_item")

    # Constraints
    __table_args__ = (
        CheckConstraint(status.in_(['queued', 'in_progress', 'pr_ready', 'completed', 'blocked', 'cancelled']),
                       name='work_items_status_check'),
        CheckConstraint(source.in_(['azure_devops', 'jira', 'github', 'linear', 'manual']),
                       name='work_items_source_check'),
    )

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    name = Column(String(255))
    config = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime(timezone=True))
    sync_interval = Column(Integer, default=300)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team = relationship("Team", back_populates="integrations")

    # Constraints
    __table_args__ = (
        CheckConstraint(type.in_(['azure_devops', 'jira', 'github', 'linear']),
                       name='integrations_type_check'),
    )

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"))
    work_item_id = Column(UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="SET NULL"))
    event_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    team = relationship("Team", back_populates="activity_logs")
    agent = relationship("Agent", back_populates="activity_logs")
    work_item = relationship("WorkItem", back_populates="activity_logs")
```

## 5. Pydantic Schemas

Create `api/app/schemas.py`:

```python
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

# Base schemas
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
    worktree_path: Optional[str]
    current_branch: Optional[str]
    last_activity: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

# Team with agents
class TeamWithAgents(Team):
    agents: List[Agent] = []

    class Config:
        from_attributes = True
```

## 6. FastAPI Application

Create `api/app/main.py`:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from .config import settings
from .routes import teams, agents, work_items

# Create tables (for development - use Alembic in production)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="Claude-Nine API",
    description="API for managing AI development teams",
    version="1.0.0",
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0"
    }

# Database health check
@app.get("/health/db")
def db_health_check(db: Session = Depends(get_db)):
    try:
        # Try to execute a simple query
        db.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}

# Include routers
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(work_items.router, prefix="/api/work-items", tags=["work-items"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
```

## 7. Example Route

Create `api/app/routes/teams.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..database import get_db
from ..models import Team
from ..schemas import Team as TeamSchema, TeamCreate, TeamUpdate, TeamWithAgents

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
```

Create `api/app/routes/__init__.py`:

```python
# Empty file to make routes a package
```

## 8. Run the API

```bash
cd api
uvicorn app.main:app --reload
```

Visit:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## 9. Test the API

```bash
# Create a team
curl -X POST http://localhost:8000/api/teams/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Team",
    "product": "ShopifyClone",
    "repo_path": "/repos/shopify-clone"
  }'

# List teams
curl http://localhost:8000/api/teams/

# Get team by ID
curl http://localhost:8000/api/teams/{team_id}
```

## 10. Database Migrations with Alembic

Initialize Alembic:

```bash
cd api
alembic init alembic
```

Edit `alembic.ini`:

```ini
# Replace
sqlalchemy.url = driver://user:pass@localhost/dbname

# With
sqlalchemy.url = postgresql://claude_admin:password@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require
```

Or use environment variable in `alembic/env.py`:

```python
from app.config import settings

# Replace
config.set_main_option("sqlalchemy.url", "...")

# With
config.set_main_option("sqlalchemy.url", settings.database_url)
```

Create migration:

```bash
alembic revision --autogenerate -m "Initial schema"
```

Apply migration:

```bash
alembic upgrade head
```

## Complete File Structure

```
api/
├── .env
├── requirements.txt
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
└── app/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── database.py
    ├── models.py
    ├── schemas.py
    └── routes/
        ├── __init__.py
        ├── teams.py
        ├── agents.py
        └── work_items.py
```

---

**You're now ready to start building the FastAPI backend!** 🚀
