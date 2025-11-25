# Claude-Nine Implementation Roadmap

## Current State Assessment

### ✅ What We Have

**Core Orchestration** (`claude-multi-agent-orchestrator/`)
- ✅ Multi-agent orchestrator using CrewAI
- ✅ Git worktree isolation for agents
- ✅ Parallel agent execution
- ✅ Monitor agent for conflict detection
- ✅ Git operations wrapper (branches, commits, merges)
- ✅ Git tools for agents (10 tools: create branch, commit, write file, etc.)
- ✅ YAML-based task definition
- ✅ Logging to `.agent-workspace/orchestrator.log`
- ✅ Graceful cleanup and signal handling

**Dependencies**
- CrewAI >= 0.80.0
- GitPython >= 3.1.40
- Anthropic >= 0.39.0
- PyYAML >= 6.0.1

### ❌ What We Need to Build

**Web UI**
- ❌ Frontend dashboard (Next.js + React)
- ❌ Backend API (FastAPI)
- ❌ Real-time WebSocket updates
- ❌ Database for state management (PostgreSQL)

**PM Tool Integrations**
- ❌ Azure DevOps API client
- ❌ Jira API client
- ❌ GitHub Issues client
- ❌ Work item sync service

**Enhanced Orchestrator**
- ❌ Pull work from PM tools (vs. YAML files)
- ❌ Multi-team management
- ❌ Team lifecycle (start/stop/pause)
- ❌ Work queue management
- ❌ Status reporting to web UI

---

## Implementation Phases

## Phase 1: Foundation (Weeks 1-2)

**Goal**: Set up project structure, database, and basic API

### Tasks

1. **Project Restructure**
   ```
   claude-nine/
   ├── api/                    # FastAPI backend (NEW)
   ├── dashboard/              # Next.js frontend (NEW)
   ├── orchestrator/           # Refactored from claude-multi-agent-orchestrator
   ├── integrations/           # PM tool clients (NEW)
   ├── shared/                 # Shared models/types (NEW)
   ├── docs/                   # Documentation
   ├── VISION.md
   └── ROADMAP.md
   ```

2. **Database Setup**
   - Install PostgreSQL
   - Create database schema (teams, agents, work_items, integrations)
   - Set up migrations (Alembic)
   - Seed data for testing

3. **API Foundation**
   - Set up FastAPI project structure
   - Database connection and ORM (SQLAlchemy)
   - Basic CRUD endpoints for teams
   - Health check endpoint
   - CORS configuration for frontend

4. **Frontend Foundation**
   - Create Next.js project with TypeScript
   - Set up Tailwind CSS
   - Install shadcn-ui components
   - Create basic layout and routing
   - Configure API client (fetch wrapper)

### Deliverable
- ✅ Database running with schema
- ✅ API server running on http://localhost:8000
- ✅ Frontend running on http://localhost:3000
- ✅ Can create and list teams via API

---

## Phase 2: Core Features (Weeks 3-5)

**Goal**: Build team management and basic monitoring

### Tasks

1. **Team Management API**
   - POST `/api/teams` - Create team
   - GET `/api/teams` - List all teams
   - GET `/api/teams/{id}` - Get team details
   - PUT `/api/teams/{id}` - Update team
   - DELETE `/api/teams/{id}` - Delete team
   - POST `/api/teams/{id}/start` - Start team
   - POST `/api/teams/{id}/stop` - Stop team
   - POST `/api/teams/{id}/pause` - Pause team

2. **Agent Management API**
   - GET `/api/teams/{id}/agents` - List agents for team
   - GET `/api/agents/{id}` - Get agent details
   - GET `/api/agents/{id}/status` - Get agent status
   - GET `/api/agents/{id}/logs` - Stream agent logs

3. **Orchestrator Integration**
   - Refactor orchestrator to be importable as library
   - Add orchestrator manager service (start/stop teams)
   - Expose orchestrator state to API
   - Add callbacks for status updates
   - Store team/agent state in database

4. **Frontend - Team Management**
   - Dashboard home page (team overview)
   - Team list with status indicators
   - Team creation modal/form
   - Team detail page
   - Agent list for team
   - Start/stop/pause controls

### Deliverable
- ✅ Can create teams from web UI
- ✅ Can start/stop teams
- ✅ Can see team status (active, paused, stopped)
- ✅ Can view agents in a team

---

## Phase 3: Azure DevOps Integration (Weeks 6-7)

**Goal**: Pull work items from Azure DevOps

### Tasks

1. **Azure DevOps Client** (`integrations/azure_devops.py`)
   ```python
   class AzureDevOpsClient:
       - connect(organization, project, pat)
       - get_work_items(query_id)
       - get_work_item(id)
       - update_work_item_status(id, status)
       - add_comment(id, comment)
       - get_work_item_url(id)
   ```

2. **Integration Configuration API**
   - POST `/api/integrations` - Add integration
   - GET `/api/integrations/{team_id}` - Get team's integration
   - PUT `/api/integrations/{id}` - Update integration
   - POST `/api/integrations/{id}/test` - Test connection

3. **Work Item Sync Service**
   - Background worker to poll ADO for new work items
   - Sync work items to database
   - Map ADO status to Claude-Nine status
   - Handle work item updates

4. **Work Queue API**
   - GET `/api/teams/{id}/work-queue` - Get team's work queue
   - POST `/api/teams/{id}/work-queue` - Assign work item to team
   - GET `/api/work-items/{id}` - Get work item details
   - PUT `/api/work-items/{id}/status` - Update status

5. **Frontend - Integration Setup**
   - Integration configuration form
   - ADO connection test
   - Work item list view
   - Drag-and-drop work assignment
   - Work queue display per team

### Deliverable
- ✅ Can configure ADO integration
- ✅ Can pull PBIs from ADO query
- ✅ Can assign PBIs to teams
- ✅ Teams pull work from queue (not YAML files)

---

## Phase 4: Real-Time Monitoring (Weeks 8-9)

**Goal**: Live dashboard updates via WebSockets

### Tasks

1. **WebSocket Server**
   - Set up WebSocket endpoint in FastAPI
   - Connection management (subscribe to teams/agents)
   - Event broadcasting system
   - Reconnection handling

2. **Orchestrator Events**
   - Emit events for agent status changes
   - Emit events for commits
   - Emit events for conflicts
   - Emit events for task completion

3. **Frontend - WebSocket Client**
   - WebSocket hook (`useWebSocket`)
   - Real-time team status updates
   - Real-time agent activity updates
   - Live log streaming
   - Toast notifications for events

4. **Enhanced Dashboard**
   - Live activity feed
   - Agent status cards with real-time updates
   - Progress bars for current work
   - Conflict alerts
   - Recent commits list

### Deliverable
- ✅ Dashboard updates in real-time without refresh
- ✅ See agent activity as it happens
- ✅ Get notified of conflicts immediately
- ✅ Stream logs in browser

---

## Phase 5: Status Sync & Polish (Weeks 10-11)

**Goal**: Bidirectional sync with ADO and production readiness

### Tasks

1. **Status Update Service**
   - On work start → Update ADO: New → Active
   - On PR ready → Update ADO: Active → Resolved
   - On completion → Update ADO: Resolved → Closed
   - On conflict → Add comment to ADO work item
   - Include links to commits/branches in comments

2. **Metrics & Analytics**
   - Team velocity tracking (stories/day)
   - Agent utilization metrics
   - Completion rates
   - Bottleneck identification
   - Charts and graphs

3. **Error Handling & Resilience**
   - Graceful degradation if ADO is down
   - Retry logic for API calls
   - Error notifications to Director
   - Agent recovery from failures

4. **Polish & UX**
   - Loading states
   - Error messages
   - Confirmation dialogs
   - Keyboard shortcuts
   - Dark mode support
   - Mobile-responsive design

### Deliverable
- ✅ Status updates flow back to ADO automatically
- ✅ Metrics dashboard shows team performance
- ✅ System handles errors gracefully
- ✅ Professional, polished UI

---

## Phase 6: Additional Integrations (Weeks 12-13)

**Goal**: Support Jira, GitHub Issues, Linear

### Tasks

1. **Jira Client** (`integrations/jira.py`)
   - Similar to ADO client but for Jira API
   - JQL query support
   - Issue transition workflow
   - Comment support

2. **GitHub Client** (`integrations/github.py`)
   - GitHub REST/GraphQL API
   - Pull issues from repos
   - Update labels and status
   - Comment on issues

3. **Integration Registry**
   - Plugin architecture for integrations
   - Unified interface for all PM tools
   - Configuration per integration type
   - Status mapping configuration

4. **Frontend - Multi-Integration**
   - Select integration type (ADO, Jira, GitHub)
   - Dynamic config forms per type
   - Multi-source work queue
   - Filter by source

### Deliverable
- ✅ Support for ADO, Jira, and GitHub
- ✅ Director can choose preferred PM tool
- ✅ Teams can pull from different sources

---

## Phase 7: Advanced Features (Weeks 14+)

**Goal**: Enterprise features and scaling

### Tasks (Future)

1. **Multi-Repository Support**
   - Teams work on different repos
   - Cross-repo dependencies
   - Monorepo support

2. **Team Templates**
   - Predefined team configurations
   - Clone team setup
   - Agent role library

3. **Advanced Analytics**
   - Predictive completion times
   - Resource optimization suggestions
   - Trend analysis

4. **Notifications**
   - Slack integration
   - Email notifications
   - Teams/Discord webhooks

5. **Security & Auth**
   - User authentication
   - Role-based access control
   - Team permissions
   - Audit logs

6. **Deployment**
   - Docker Compose setup
   - Kubernetes manifests
   - CI/CD pipeline
   - Production deployment guide

---

## Technical Stack Summary

### Backend
- **Framework**: FastAPI 0.100+
- **Database**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **WebSockets**: FastAPI WebSocket
- **Background Jobs**: APScheduler or Celery
- **Testing**: pytest

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn-ui
- **State**: React Query (TanStack Query)
- **WebSocket**: native WebSocket API
- **Testing**: Jest, React Testing Library

### Orchestrator
- **Framework**: CrewAI 0.80+
- **LLM**: Anthropic Claude (via API)
- **Git**: GitPython
- **Configuration**: YAML

### Integrations
- **Azure DevOps**: azure-devops Python package
- **Jira**: jira Python package
- **GitHub**: PyGithub or httpx
- **Linear**: Linear API client

---

## Quick Start Guide (For Developers)

### Prerequisites
```bash
# System dependencies
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Git

# Environment variables
export ANTHROPIC_API_KEY="your-key"
export DATABASE_URL="postgresql://user:pass@localhost/claude_nine"
export ADO_PAT="your-azure-devops-pat"
```

### Phase 1 Setup

1. **Database**
   ```bash
   createdb claude_nine
   cd api
   alembic upgrade head
   ```

2. **Backend**
   ```bash
   cd api
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. **Frontend**
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```

4. **Test**
   ```
   Open http://localhost:3000
   Create your first team
   Spin it up!
   ```

---

## Success Metrics

### Phase 1
- [ ] Database schema created and running
- [ ] API returns team data
- [ ] Frontend displays team list

### Phase 2
- [ ] Can create team from UI
- [ ] Can start/stop team
- [ ] See agents in team

### Phase 3
- [ ] Pull work from Azure DevOps
- [ ] Assign work to team
- [ ] Team works on ADO PBI

### Phase 4
- [ ] Dashboard updates in real-time
- [ ] See live agent activity
- [ ] Log streaming works

### Phase 5
- [ ] Status updates flow to ADO
- [ ] Metrics dashboard shows data
- [ ] Professional UI/UX

### Phase 6
- [ ] Jira integration works
- [ ] GitHub integration works
- [ ] Can mix sources

---

## Next Immediate Steps

### Step 1: Project Setup (Today)
```bash
# Create new directories
mkdir -p api/app/{routes,models,services,integrations}
mkdir -p dashboard/{app,components,lib,hooks}
mkdir -p shared/models

# Initialize backend
cd api
touch main.py requirements.txt
touch app/{__init__,database,config}.py

# Initialize frontend
cd ../dashboard
npx create-next-app@latest . --typescript --tailwind --app
```

### Step 2: Database Schema (Today)
```sql
-- Create initial schema
-- See detailed schema in VISION.md
```

### Step 3: First API Endpoint (Tomorrow)
```python
# api/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/teams")
def list_teams():
    return {"teams": []}
```

### Step 4: First UI Page (Tomorrow)
```typescript
// dashboard/app/page.tsx
export default function Home() {
  return <div>Claude-Nine Dashboard</div>
}
```

---

## Questions to Answer Before Starting

1. **Database**: PostgreSQL locally or Docker container?
2. **Monorepo**: Keep everything in claude-nine/ or separate repos?
3. **Orchestrator**: Refactor in place or copy to new location?
4. **PM Tool**: Start with Azure DevOps or Jira first?
5. **Deployment**: Target local-only or cloud deployment from start?

---

## Conclusion

This roadmap takes us from the current multi-agent orchestrator to a full-featured web-based platform for managing AI development teams. Each phase builds on the previous one, with clear deliverables and success metrics.

**Estimated Timeline**: 11-13 weeks for Phases 1-6
**Minimum Viable Product**: End of Phase 3 (7 weeks)
**Production Ready**: End of Phase 5 (11 weeks)

Ready to start building? 🚀
