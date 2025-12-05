# Seed Database

Populate the Claude-Nine database with test data for development and testing.

## When to Use

- After resetting the database
- When setting up a new development environment
- For demo purposes
- When testing UI with sample data

## Instructions

### Option 1: Reset and Seed (Recommended)

This resets the database AND adds test data:

```bash
cd api
source ../venv/bin/activate  # Linux/Mac
# OR: . ../venv/Scripts/activate  # Windows

python reset_and_seed.py
```

### Option 2: Seed Only (Keep Existing Data)

Add test data without resetting:

```bash
cd api
source ../venv/bin/activate

python seed_test_data.py
```

## What Gets Created

### Teams

| Name | Product | Repo Path |
|------|---------|-----------|
| Alpha Team | Schematics App | /c/projects/schematics |
| Beta Team | Dashboard | /c/projects/dashboard |

### Work Items

| Title | Status | Priority |
|-------|--------|----------|
| Implement authentication | queued | 1 |
| Add logging system | queued | 2 |
| Create documentation | queued | 3 |
| Setup CI/CD pipeline | queued | 2 |
| Implement dark mode | queued | 3 |

### Personas

| Name | Type | Description |
|------|------|-------------|
| Senior Developer | dev | Experienced full-stack developer |
| Junior Developer | dev | Eager learner with fresh perspective |
| Tech Lead | dev | Architecture and code review focus |
| DevOps Engineer | dev | Infrastructure and deployment |

## Custom Seed Data

To create custom test data, modify or create a seed script:

```python
# api/custom_seed.py
from app.database import SessionLocal, engine
from app import models
import uuid

def seed():
    db = SessionLocal()
    try:
        # Create team
        team = models.Team(
            id=uuid.uuid4(),
            name="My Test Team",
            product="Test Product",
            repo_path="/path/to/repo",
            main_branch="main",
            status="active"
        )
        db.add(team)

        # Create work items
        for i in range(5):
            work_item = models.WorkItem(
                id=uuid.uuid4(),
                team_id=team.id,
                title=f"Test Work Item {i+1}",
                description=f"Description for item {i+1}",
                source="manual",
                status="queued",
                priority=i % 3 + 1
            )
            db.add(work_item)

        db.commit()
        print(f"Created team: {team.id}")
        print("Created 5 work items")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
```

Run:
```bash
cd api
python custom_seed.py
```

## Verify Seed Data

### Via API

```bash
# List teams
curl http://localhost:8000/api/teams | jq .

# List work items
curl http://localhost:8000/api/work-items | jq .

# List personas
curl http://localhost:8000/api/personas | jq .
```

### Via Database

```bash
cd api
sqlite3 claude_nine.db "SELECT id, name, status FROM teams;"
sqlite3 claude_nine.db "SELECT id, title, status FROM work_items;"
```

### Via Dashboard

1. Open http://localhost:3001
2. Navigate to Teams → Should see seeded teams
3. Click team → Should see work items

## Clear Seed Data

To remove all data without dropping schema:

```bash
cd api
sqlite3 claude_nine.db "
DELETE FROM run_tasks;
DELETE FROM runs;
DELETE FROM work_items;
DELETE FROM agents;
DELETE FROM teams;
DELETE FROM activity_logs;
"
```

## Troubleshooting

### "Team already exists"

Seed scripts may fail if data already exists. Reset first:
```bash
python reset_and_seed.py
```

### "Foreign key constraint failed"

Delete child records first, or use reset script which handles order.

### "Database is locked"

Stop the API server before seeding:
```bash
pkill -f uvicorn
python seed_test_data.py
uvicorn app.main:app --reload
```
