from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import TypeDecorator
import uuid

from .database import Base


# UUID type that works with both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(value)
            except (ValueError, AttributeError):
                pass
        return value


class Team(Base):
    __tablename__ = "teams"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
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

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
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

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id", ondelete="SET NULL"))
    external_id = Column(String(255), nullable=False)
    source = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    acceptance_criteria = Column(Text)
    status = Column(String(50), nullable=False, default="queued")
    priority = Column(Integer, default=0)
    story_points = Column(Integer)
    external_url = Column(String(500))
    external_data = Column(JSON)
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

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    name = Column(String(255))
    config = Column(JSON, nullable=False)
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

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id", ondelete="CASCADE"))
    agent_id = Column(GUID(), ForeignKey("agents.id", ondelete="CASCADE"))
    work_item_id = Column(GUID(), ForeignKey("work_items.id", ondelete="SET NULL"))
    event_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    event_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    team = relationship("Team", back_populates="activity_logs")
    agent = relationship("Agent", back_populates="activity_logs")
    work_item = relationship("WorkItem", back_populates="activity_logs")
