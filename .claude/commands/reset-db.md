# Reset Database

Reset the Claude-Nine database to a fresh state.

## Instructions

1. **Stop the API server first** (important to release database lock):
   ```bash
   pkill -f "uvicorn app.main:app"
   # Or use /stop command
   ```

2. **Backup current database** (optional but recommended):
   ```bash
   cd api
   cp claude_nine.db claude_nine.db.backup.$(date +%Y%m%d_%H%M%S)
   ```

3. **Reset the database**:
   ```bash
   cd api
   source ../venv/bin/activate  # Linux/Mac
   # OR: . ../venv/Scripts/activate  # Windows
   python reset_db.py
   ```

4. **Verify reset**:
   ```bash
   # Check database file exists and is small (empty)
   ls -la claude_nine.db
   # Should be ~12KB (just schema, no data)
   ```

5. **Restart API**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## What This Does

- Drops all existing tables
- Recreates tables from SQLAlchemy models
- Results in empty database with fresh schema

## Alternative: Reset with Test Data

If you want sample data immediately:
```bash
cd api
python reset_and_seed.py
```

This creates:
- 2-3 sample teams
- Sample work items
- Sample personas

## Database Location

```
api/claude_nine.db  (SQLite file)
```

## Troubleshooting

- **"Database is locked"**: Stop the API server first
- **Permission denied**: Check file permissions on claude_nine.db
- **Import errors**: Ensure venv is activated and requirements installed

## Manual Reset (if scripts fail)

```bash
cd api
rm claude_nine.db
rm -f claude_nine.db-journal  # Remove any lock file
python -c "from app.database import engine, Base; from app import models; Base.metadata.create_all(bind=engine)"
```
