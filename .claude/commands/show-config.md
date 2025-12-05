# Show Configuration

Display current Claude-Nine configuration and environment settings.

## Quick Config Check

```bash
echo "=== Environment Variables ==="
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:12}..."
echo "DATABASE_URL: $DATABASE_URL"
echo "API_HOST: ${API_HOST:-0.0.0.0}"
echo "API_PORT: ${API_PORT:-8000}"
echo "DEBUG: ${DEBUG:-False}"
echo "FORCE_DRY_RUN: ${FORCE_DRY_RUN:-False}"

echo ""
echo "=== .env File ==="
cat api/.env 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "No .env file found"

echo ""
echo "=== Database ==="
ls -la api/claude_nine.db 2>/dev/null || echo "Database not found"

echo ""
echo "=== Python Environment ==="
which python
python --version

echo ""
echo "=== Node Environment ==="
which node
node --version
```

## Configuration Files

### API Configuration

**Location**: `api/.env`

```bash
# View (masks sensitive values)
cat api/.env | sed 's/\(API_KEY=\).*/\1***MASKED***/'
```

**Default values**:
```bash
DATABASE_URL=sqlite:///./claude_nine.db
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False
FORCE_DRY_RUN=False
SECRET_KEY=change-me-in-production
ANTHROPIC_API_KEY=sk-ant-...
ADO_PAT=  # Optional: Azure DevOps
```

### Orchestrator Configuration

**Location**: Generated at runtime or `config.yaml`

```yaml
# Example config.yaml
repo_path: /path/to/target/repo
main_branch: main
max_concurrent_agents: 4
workspace_dir: .agent-workspace
session_id: auto-generated

llm:
  model: claude-sonnet-4-20250514
  temperature: 0.7
  max_tokens: 4096

telemetry:
  enabled: true
  api_url: http://localhost:8000
  interval_seconds: 2
```

### Task Configuration

**Location**: `claude-multi-agent-orchestrator/tasks/`

```bash
# List available task files
ls -la claude-multi-agent-orchestrator/tasks/

# View task file
cat claude-multi-agent-orchestrator/tasks/example_tasks.yaml
```

## Get Config via API

```bash
# Get settings (API key masked)
curl http://localhost:8000/api/settings | jq .

# Get unmasked config (for orchestrator subprocess)
curl http://localhost:8000/api/settings/orchestrator/config | jq .
```

## Database Configuration

```bash
# Check database URL
sqlite3 api/claude_nine.db ".databases"

# Check tables
sqlite3 api/claude_nine.db ".tables"

# Check record counts
sqlite3 api/claude_nine.db "
SELECT 'teams' as tbl, COUNT(*) as cnt FROM teams
UNION ALL SELECT 'work_items', COUNT(*) FROM work_items
UNION ALL SELECT 'runs', COUNT(*) FROM runs
UNION ALL SELECT 'run_tasks', COUNT(*) FROM run_tasks;
"
```

## Dashboard Configuration

**Location**: `dashboard/.env.local`

```bash
# View dashboard config
cat dashboard/.env.local 2>/dev/null || echo "Using default config"
```

**Default values**:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Modify Configuration

### Change API Port

```bash
# In api/.env
API_PORT=8080

# Restart API
pkill -f uvicorn
cd api && uvicorn app.main:app --reload --port 8080
```

### Enable Debug Mode

```bash
# In api/.env
DEBUG=True

# Or via environment
DEBUG=True uvicorn app.main:app --reload
```

### Force Dry-Run Mode

```bash
# In api/.env
FORCE_DRY_RUN=True

# All runs will use mock LLM
```

### Change Database

```bash
# SQLite (default)
DATABASE_URL=sqlite:///./claude_nine.db

# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/claude_nine
```

## Validate Configuration

```bash
# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'

# Test database connection
curl http://localhost:8000/health/db

# Test WebSocket
wscat -c ws://localhost:8000/ws
# Type: {"action": "ping"}
```

## Configuration Precedence

1. **Environment variables** (highest priority)
2. **.env file** in api/
3. **Default values** in config.py

```python
# Example: API_PORT
# 1. os.environ.get("API_PORT") -> "9000"
# 2. .env: API_PORT=8080
# 3. config.py: api_port: int = 8000

# Result: 9000 (environment wins)
```
