# Claude-Nine Quick Start Guide

Get up and running with Claude-Nine in 5 minutes using SQLite (swap to PostgreSQL later).

## Prerequisites

- Python 3.12+
- pip
- curl (for testing)
- jq (optional, for pretty JSON output)

## Step 1: Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

## Step 2: Start the API

```bash
# Option A: Using the run script
./run.sh

# Option B: Manually
uvicorn app.main:app --reload
```

The API will start on http://localhost:8000

## Step 3: Verify It's Working

Open your browser to:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see the interactive OpenAPI documentation!

## Step 4: Test the API

Run the test script:

```bash
./test_api.sh
```

This will:
1. ✅ Check health endpoints
2. ✅ Create a team
3. ✅ Add agents to the team
4. ✅ Create a work item
5. ✅ Start the team

## Step 5: Explore the API

### Using the Interactive Docs

Visit http://localhost:8000/docs and try:
- Click on any endpoint
- Click "Try it out"
- Fill in parameters
- Click "Execute"

### Using curl

**Create a Team:**
```bash
curl -X POST http://localhost:8000/api/teams/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Team",
    "product": "My Product",
    "repo_path": "/repos/my-product"
  }'
```

**List Teams:**
```bash
curl http://localhost:8000/api/teams/
```

**Add an Agent:**
```bash
curl -X POST http://localhost:8000/api/teams/{team_id}/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "developer_agent",
    "role": "Full Stack Developer",
    "goal": "Build amazing features"
  }'
```

## Database

Currently using SQLite (`claude_nine.db` file) for development.

### View the Database

```bash
# Install sqlite3 if needed
sqlite3 api/claude_nine.db

# Inside sqlite3:
.tables
SELECT * FROM teams;
SELECT * FROM agents;
.quit
```

### Switch to PostgreSQL Later

When your Azure PostgreSQL is ready:

1. Update `api/.env`:
   ```bash
   DATABASE_URL=postgresql://claude_admin:password@claude-nine-db.postgres.database.azure.com:5432/claude_nine?sslmode=require
   ```

2. Restart the API:
   ```bash
   ./run.sh
   ```

That's it! SQLAlchemy handles both SQLite and PostgreSQL seamlessly.

## Next Steps

1. ✅ API is running with SQLite
2. 🔄 Start building the Next.js dashboard
3. 🔄 Test team creation and management
4. ⏳ When PostgreSQL is ready, swap connection string

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Address already in use"
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### "Database locked" error
```bash
# SQLite issue - just restart the API
# Or delete the DB file and restart:
rm claude_nine.db
./run.sh
```

## File Structure

```
api/
├── claude_nine.db      # SQLite database (auto-created)
├── run.sh              # Start the API
├── test_api.sh         # Test all endpoints
├── .env                # Environment config (SQLite for now)
└── app/                # Application code
```

---

**You're ready to go!** 🚀

Start the API: `./run.sh`
Test it: `./test_api.sh`
Explore: http://localhost:8000/docs
