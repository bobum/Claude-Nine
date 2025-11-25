# Claude-Nine Database Schema

## Overview

This document contains the complete database schema for Claude-Nine, including DDL statements for PostgreSQL.

## Schema Diagram

```
┌─────────────┐         ┌─────────────┐         ┌──────────────┐
│    teams    │────────<│   agents    │         │ integrations │
│             │         │             │         │              │
│ id          │         │ id          │         │ id           │
│ name        │         │ team_id (FK)│<────────│ team_id (FK) │
│ product     │         │ name        │         │ type         │
│ repo_path   │         │ role        │         │ config       │
│ status      │         │ status      │         └──────────────┘
└─────────────┘         └─────────────┘
      │
      │                 ┌──────────────┐
      └────────────────<│  work_items  │
                        │              │
                        │ id           │
                        │ team_id (FK) │
                        │ external_id  │
                        │ source       │
                        │ title        │
                        │ status       │
                        └──────────────┘
```

## DDL Statements

### 1. Enable Extensions

```sql
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable timestamp functions
CREATE EXTENSION IF NOT EXISTS "btree_gist";
```

### 2. Teams Table

```sql
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    product VARCHAR(255) NOT NULL,
    repo_path VARCHAR(500) NOT NULL,
    main_branch VARCHAR(100) DEFAULT 'main',
    status VARCHAR(50) NOT NULL DEFAULT 'stopped',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT teams_status_check CHECK (status IN ('active', 'paused', 'stopped', 'error')),
    CONSTRAINT teams_name_unique UNIQUE (name)
);

-- Index for common queries
CREATE INDEX idx_teams_status ON teams(status);
CREATE INDEX idx_teams_product ON teams(product);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE teams IS 'Development teams managed by Claude-Nine';
COMMENT ON COLUMN teams.status IS 'Team status: active, paused, stopped, error';
```

### 3. Agents Table

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    goal TEXT,
    worktree_path VARCHAR(500),
    current_branch VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'idle',
    last_activity TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT agents_status_check CHECK (status IN ('idle', 'working', 'blocked', 'error')),
    CONSTRAINT agents_team_name_unique UNIQUE (team_id, name)
);

-- Indexes
CREATE INDEX idx_agents_team_id ON agents(team_id);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_last_activity ON agents(last_activity DESC);

-- Auto-update trigger
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE agents IS 'AI agents (developers) belonging to teams';
COMMENT ON COLUMN agents.status IS 'Agent status: idle, working, blocked, error';
```

### 4. Work Items Table

```sql
CREATE TABLE work_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    external_id VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    acceptance_criteria TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    priority INTEGER DEFAULT 0,
    story_points INTEGER,
    external_url VARCHAR(500),
    external_data JSONB,
    assigned_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT work_items_status_check CHECK (status IN ('queued', 'in_progress', 'pr_ready', 'completed', 'blocked', 'cancelled')),
    CONSTRAINT work_items_source_check CHECK (source IN ('azure_devops', 'jira', 'github', 'linear', 'manual')),
    CONSTRAINT work_items_source_id_unique UNIQUE (source, external_id)
);

-- Indexes
CREATE INDEX idx_work_items_team_id ON work_items(team_id);
CREATE INDEX idx_work_items_status ON work_items(status);
CREATE INDEX idx_work_items_source ON work_items(source);
CREATE INDEX idx_work_items_external_id ON work_items(source, external_id);
CREATE INDEX idx_work_items_priority ON work_items(priority DESC);
CREATE INDEX idx_work_items_assigned_at ON work_items(assigned_at DESC NULLS LAST);

-- JSONB index for querying external data
CREATE INDEX idx_work_items_external_data ON work_items USING GIN (external_data);

-- Auto-update trigger
CREATE TRIGGER update_work_items_updated_at BEFORE UPDATE ON work_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE work_items IS 'User stories/PBIs/Issues from external PM tools';
COMMENT ON COLUMN work_items.external_data IS 'Full JSON response from source system (ADO, Jira, etc)';
```

### 5. Integrations Table

```sql
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_sync TIMESTAMP WITH TIME ZONE,
    sync_interval INTEGER DEFAULT 300,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT integrations_type_check CHECK (type IN ('azure_devops', 'jira', 'github', 'linear')),
    CONSTRAINT integrations_team_type_unique UNIQUE (team_id, type)
);

-- Indexes
CREATE INDEX idx_integrations_team_id ON integrations(team_id);
CREATE INDEX idx_integrations_type ON integrations(type);
CREATE INDEX idx_integrations_is_active ON integrations(is_active);

-- JSONB index for config queries
CREATE INDEX idx_integrations_config ON integrations USING GIN (config);

-- Auto-update trigger
CREATE TRIGGER update_integrations_updated_at BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE integrations IS 'PM tool integrations (ADO, Jira, GitHub, etc)';
COMMENT ON COLUMN integrations.config IS 'Integration-specific config (API keys, queries, etc)';
```

### 6. Activity Logs Table

```sql
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    work_item_id UUID REFERENCES work_items(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_activity_logs_team_id ON activity_logs(team_id);
CREATE INDEX idx_activity_logs_agent_id ON activity_logs(agent_id);
CREATE INDEX idx_activity_logs_work_item_id ON activity_logs(work_item_id);
CREATE INDEX idx_activity_logs_event_type ON activity_logs(event_type);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);

-- Partition by month (optional, for large-scale deployments)
-- CREATE TABLE activity_logs_2025_01 PARTITION OF activity_logs
--     FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

COMMENT ON TABLE activity_logs IS 'Audit trail of all team/agent/work item activities';
COMMENT ON COLUMN activity_logs.event_type IS 'e.g., agent_started, commit_created, conflict_detected, work_completed';
```

### 7. Metrics Table (Optional)

```sql
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    stories_completed INTEGER DEFAULT 0,
    commits_count INTEGER DEFAULT 0,
    conflicts_count INTEGER DEFAULT 0,
    avg_completion_time_hours NUMERIC(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT metrics_team_date_unique UNIQUE (team_id, metric_date)
);

-- Indexes
CREATE INDEX idx_metrics_team_id ON metrics(team_id);
CREATE INDEX idx_metrics_date ON metrics(metric_date DESC);

COMMENT ON TABLE metrics IS 'Daily metrics for team performance tracking';
```

## Views

### Active Teams with Agent Counts

```sql
CREATE VIEW v_active_teams AS
SELECT
    t.id,
    t.name,
    t.product,
    t.status,
    COUNT(a.id) as agent_count,
    COUNT(CASE WHEN a.status = 'working' THEN 1 END) as active_agents,
    COUNT(CASE WHEN w.status = 'queued' THEN 1 END) as queued_work_items,
    COUNT(CASE WHEN w.status = 'in_progress' THEN 1 END) as in_progress_work_items
FROM teams t
LEFT JOIN agents a ON t.id = a.team_id
LEFT JOIN work_items w ON t.id = w.team_id
WHERE t.status IN ('active', 'paused')
GROUP BY t.id, t.name, t.product, t.status;

COMMENT ON VIEW v_active_teams IS 'Active teams with agent and work item counts';
```

### Team Work Queue

```sql
CREATE VIEW v_team_work_queue AS
SELECT
    w.id,
    w.team_id,
    t.name as team_name,
    w.external_id,
    w.source,
    w.title,
    w.status,
    w.priority,
    w.assigned_at,
    w.started_at,
    w.external_url
FROM work_items w
JOIN teams t ON w.team_id = t.id
WHERE w.status IN ('queued', 'in_progress', 'pr_ready')
ORDER BY w.priority DESC, w.assigned_at ASC;

COMMENT ON VIEW v_team_work_queue IS 'Active work queue across all teams';
```

## Initial Data / Seed Data

```sql
-- Example team
INSERT INTO teams (name, product, repo_path, status) VALUES
    ('Demo Team', 'Demo Product', '/repos/demo', 'stopped');

-- Example agents for demo team
INSERT INTO agents (team_id, name, role, goal, status)
SELECT
    id,
    'backend_agent',
    'Backend Developer',
    'Build robust APIs and backend services',
    'idle'
FROM teams WHERE name = 'Demo Team';

INSERT INTO agents (team_id, name, role, goal, status)
SELECT
    id,
    'frontend_agent',
    'Frontend Developer',
    'Create responsive user interfaces',
    'idle'
FROM teams WHERE name = 'Demo Team';
```

## Useful Queries

### Get Team Overview

```sql
SELECT
    t.name,
    t.status,
    COUNT(DISTINCT a.id) as total_agents,
    COUNT(DISTINCT CASE WHEN w.status = 'completed' THEN w.id END) as completed_stories,
    COUNT(DISTINCT CASE WHEN w.status = 'in_progress' THEN w.id END) as active_stories,
    COUNT(DISTINCT CASE WHEN w.status = 'queued' THEN w.id END) as queued_stories
FROM teams t
LEFT JOIN agents a ON t.id = a.team_id
LEFT JOIN work_items w ON t.id = w.team_id
GROUP BY t.id, t.name, t.status
ORDER BY t.name;
```

### Get Recent Activity

```sql
SELECT
    al.created_at,
    t.name as team_name,
    a.name as agent_name,
    al.event_type,
    al.message
FROM activity_logs al
LEFT JOIN teams t ON al.team_id = t.id
LEFT JOIN agents a ON al.agent_id = a.id
ORDER BY al.created_at DESC
LIMIT 50;
```

### Team Velocity (Last 7 Days)

```sql
SELECT
    t.name,
    COUNT(w.id) as stories_completed,
    ROUND(AVG(EXTRACT(EPOCH FROM (w.completed_at - w.started_at)) / 3600), 2) as avg_hours_per_story
FROM teams t
JOIN work_items w ON t.id = w.team_id
WHERE w.status = 'completed'
  AND w.completed_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY t.id, t.name
ORDER BY stories_completed DESC;
```

## Migration Script (Complete Setup)

Save this as `setup_schema.sql` and run:

```bash
psql "postgresql://claude_admin:<password>@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require" < setup_schema.sql
```

Or via Python:

```python
import psycopg2

conn_string = "postgresql://..."
conn = psycopg2.connect(conn_string)
cursor = conn.cursor()

with open('setup_schema.sql', 'r') as f:
    cursor.execute(f.read())

conn.commit()
cursor.close()
conn.close()
print("✅ Schema created successfully!")
```

## Backup & Restore

### Backup Schema

```bash
pg_dump -h claude-nine-db.postgres.database.azure.com \
        -U claude_admin \
        -d claude_nine \
        --schema-only \
        > schema_backup.sql
```

### Backup Data

```bash
pg_dump -h claude-nine-db.postgres.database.azure.com \
        -U claude_admin \
        -d claude_nine \
        > full_backup.sql
```

### Restore

```bash
psql "postgresql://..." < full_backup.sql
```

---

**Schema Version:** 1.0
**Last Updated:** 2025-11-25
**Compatible With:** PostgreSQL 14, 15, 16
