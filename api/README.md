# Claude-Nine API

FastAPI backend for the Claude-Nine multi-agent orchestration platform.

## Quick Start

### 1. Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
cat > .env << EOF
# Database - SQLite (default for local use)
DATABASE_URL=sqlite:///./claude_nine.db

# Anthropic API Key (required)
ANTHROPIC_API_KEY=your-api-key-here

# API Server Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
EOF
```

**Optional: Using PostgreSQL instead of SQLite**

If you prefer PostgreSQL for production or higher concurrency:
```
DATABASE_URL=postgresql://username:password@localhost:5432/claude_nine
```

### 3. Run the API

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## API Endpoints

### Teams
- `GET /api/teams` - List all teams
- `POST /api/teams` - Create a team
- `GET /api/teams/{id}` - Get team details
- `PUT /api/teams/{id}` - Update team
- `DELETE /api/teams/{id}` - Delete team
- `POST /api/teams/{id}/start` - Start team
- `POST /api/teams/{id}/stop` - Stop team
- `POST /api/teams/{id}/pause` - Pause team
- `POST /api/teams/{id}/agents` - Add agent to team

### Agents
- `GET /api/agents` - List all agents
- `GET /api/agents/{id}` - Get agent details
- `GET /api/agents/{id}/status` - Get agent status
- `DELETE /api/agents/{id}` - Delete agent

### Work Items
- `GET /api/work-items` - List work items (supports filtering)
- `POST /api/work-items` - Create work item
- `GET /api/work-items/{id}` - Get work item details
- `PUT /api/work-items/{id}` - Update work item
- `DELETE /api/work-items/{id}` - Delete work item
- `POST /api/work-items/bulk-assign` - Bulk assign items to team ⭐ **New**

## Example Usage

### Create a Team

```bash
curl -X POST http://localhost:8000/api/teams/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce Team",
    "product": "ShopifyClone",
    "repo_path": "/repos/shopify-clone"
  }'
```

### Add Agents to Team

```bash
curl -X POST http://localhost:8000/api/teams/{team_id}/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend_agent",
    "role": "Backend Developer",
    "goal": "Build robust APIs"
  }'
```

### Start a Team

```bash
curl -X POST http://localhost:8000/api/teams/{team_id}/start
```

### Bulk Assign Work Items

Assign multiple work items to a team's queue at once:

```bash
curl -X POST http://localhost:8000/api/work-items/bulk-assign \
  -H "Content-Type: application/json" \
  -d '{
    "work_item_ids": [
      "uuid-item-1",
      "uuid-item-2",
      "uuid-item-3"
    ],
    "team_id": "uuid-of-team"
  }'
```

**📚 For detailed bulk assignment documentation, see [Bulk Assignment Guide](../docs/bulk-assignment-guide.md)**

## Development

### Project Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── config.py        # Settings
│   ├── database.py      # DB connection
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   └── routes/
│       ├── teams.py
│       ├── agents.py
│       └── work_items.py
├── requirements.txt
├── .env.example
└── README.md
```

### Running Tests

```bash
pytest
```

### Database Migrations

Using Alembic:

```bash
# Initialize (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

## Deployment

See `docs/deployment.md` for production deployment instructions.
