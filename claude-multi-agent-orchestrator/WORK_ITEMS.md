# Local Work Item Management for CLAUDE-9

A standalone work item tracking system that stores items in SQLite, supports team assignment, and exports to CLAUDE-9 task format.

## Why Use This?

- **No External Dependencies**: Works without Jira, Azure DevOps, or other tools
- **Local-First**: All data stored in SQLite on your machine
- **Team Support**: Organize work items by teams
- **CLAUDE-9 Integration**: Export directly to orchestrator YAML format
- **Simple**: Easy CLI interface for managing everything

## Quick Start

### 1. Install Dependencies

```bash
pip install click tabulate
# Already included if you installed from requirements.txt
```

### 2. Create Your First Team

```bash
python work_item_cli.py team create "Backend Team" "Backend development"
```

### 3. Create a Work Item

```bash
python work_item_cli.py item create "User Authentication" \
  --description "Implement JWT auth with login/register" \
  --type feature \
  --priority high \
  --team 1 \
  --assigned-to Alice \
  --tags "auth,security" \
  --hours 16
```

### 4. Mark It Ready for CLAUDE-9

```bash
python work_item_cli.py item ready 1
```

### 5. Export and Run

```bash
# Export to YAML
python work_item_cli.py export tasks/my-work.yaml --status ready

# Run CLAUDE-9
python orchestrator.py --tasks tasks/my-work.yaml
```

## Complete CLI Reference

### Team Commands

**Create a team:**
```bash
python work_item_cli.py team create "Team Name" "Description"
```

**List all teams:**
```bash
python work_item_cli.py team list
```

**Show team summary:**
```bash
python work_item_cli.py team summary 1
```

### Work Item Commands

**Create a work item:**
```bash
python work_item_cli.py item create "Title" \
  --description "Detailed description" \
  --type [feature|bug|task|story|epic] \
  --priority [low|medium|high|critical] \
  --team TEAM_ID \
  --assigned-to "Person Name" \
  --tags "tag1,tag2,tag3" \
  --hours 8.5
```

**List work items:**
```bash
# All items
python work_item_cli.py item list

# Filter by status
python work_item_cli.py item list --status ready

# Filter by team
python work_item_cli.py item list --team 1

# Filter by type
python work_item_cli.py item list --type feature

# Filter by assignee
python work_item_cli.py item list --assigned-to Alice

# Combine filters
python work_item_cli.py item list --status ready --team 1
```

**Show item details:**
```bash
python work_item_cli.py item show 1
```

**Update a work item:**
```bash
python work_item_cli.py item update 1 \
  --status in_progress \
  --priority critical \
  --assigned-to Bob
```

**Add a comment:**
```bash
python work_item_cli.py item comment 1 "Alice" "Started working on this"
```

**Mark item as ready:**
```bash
python work_item_cli.py item ready 1
```

**Mark item as complete:**
```bash
python work_item_cli.py item complete 1
```

### Export and Run Commands

**Export to YAML:**
```bash
# Export ready items
python work_item_cli.py export tasks/work.yaml

# Export specific status
python work_item_cli.py export tasks/work.yaml --status ready

# Export for specific team
python work_item_cli.py export tasks/work.yaml --team 1
```

**Export and run in one command:**
```bash
python work_item_cli.py run tasks/work.yaml
```

**Show statistics:**
```bash
python work_item_cli.py stats
```

## Workflow Examples

### Scenario 1: Planning a Sprint

```bash
# Create teams
python work_item_cli.py team create "Backend" "API development"
python work_item_cli.py team create "Frontend" "UI development"

# Create work items
python work_item_cli.py item create "JWT Authentication" \
  --type feature --priority high --team 1 --assigned-to Alice --hours 16

python work_item_cli.py item create "API Logging" \
  --type feature --priority medium --team 1 --assigned-to Bob --hours 8

python work_item_cli.py item create "Dashboard UI" \
  --type feature --priority high --team 2 --assigned-to Carol --hours 24

# View what you have
python work_item_cli.py item list

# Mark items ready for development
python work_item_cli.py item ready 1
python work_item_cli.py item ready 2
python work_item_cli.py item ready 3

# Export and run
python work_item_cli.py run tasks/sprint-1.yaml
```

### Scenario 2: Bug Tracking

```bash
# Create a bug
python work_item_cli.py item create "Login fails with special characters" \
  --type bug \
  --priority critical \
  --team 1 \
  --assigned-to Alice \
  --tags "bug,auth,urgent"

# Add investigation notes
python work_item_cli.py item comment 1 "Alice" \
  "Found issue in password validation regex"

# Mark ready for fix
python work_item_cli.py item ready 1

# After CLAUDE-9 fixes it
python work_item_cli.py item complete 1
```

### Scenario 3: Feature Request Pipeline

```bash
# New feature request comes in
python work_item_cli.py item create "Dark Mode Support" \
  --type feature \
  --priority low \
  --team 2 \
  --description "Add dark mode toggle to settings" \
  --tags "ui,accessibility"

# During planning, update priority
python work_item_cli.py item update 1 --priority high

# Assign and mark ready
python work_item_cli.py item update 1 --assigned-to Carol
python work_item_cli.py item ready 1

# Export for this team only
python work_item_cli.py export tasks/frontend-work.yaml --team 2 --status ready
```

## Database Schema

Work items are stored in `.agent-workspace/work_items.db` with these tables:

### Teams
- id (PRIMARY KEY)
- name (UNIQUE)
- description
- created_at

### Work Items
- id (PRIMARY KEY)
- title
- description
- work_item_type (feature, bug, task, story, epic)
- status (new, ready, in_progress, completed, blocked)
- priority (low, medium, high, critical)
- team_id (FOREIGN KEY)
- assigned_to
- branch_name (auto-generated)
- estimated_hours
- tags (JSON)
- metadata (JSON)
- created_at
- updated_at

### Comments
- id (PRIMARY KEY)
- work_item_id (FOREIGN KEY)
- author
- content
- created_at

### Attachments
- id (PRIMARY KEY)
- work_item_id (FOREIGN KEY)
- filename
- file_path
- file_type
- created_at

## Programmatic Usage

You can also use the `WorkItemManager` class directly in Python:

```python
from work_item_manager import WorkItemManager

# Initialize
manager = WorkItemManager()

# Create team
team_id = manager.create_team("Backend", "Backend dev team")

# Create work item
item_id = manager.create_work_item(
    title="User Auth",
    description="Implement JWT authentication",
    work_item_type="feature",
    priority="high",
    team_id=team_id,
    assigned_to="Alice",
    tags=["auth", "security"],
    estimated_hours=16.0
)

# Add comment
manager.add_comment(item_id, "Alice", "Starting implementation")

# Mark ready
manager.mark_as_ready(item_id)

# Export to CLAUDE-9
manager.export_to_claude9_yaml('tasks/auth-work.yaml', status='ready')

# Get team summary
summary = manager.get_team_summary(team_id)
print(summary)

# Close connection
manager.close()
```

## Status Workflow

Work items follow this typical status flow:

```
new → ready → in_progress → completed
  ↓            ↓
  ↓----→ blocked
```

- **new**: Just created, not yet planned
- **ready**: Ready for CLAUDE-9 to work on
- **in_progress**: Currently being worked on
- **completed**: Finished
- **blocked**: Waiting on dependencies

## Integration with CLAUDE-9

When you export work items to YAML, they're converted to CLAUDE-9 task format:

**Work Item:**
```
Title: User Authentication
Type: feature
Description: Implement JWT auth
Team: Backend Team
Assigned: Alice
Tags: auth, security
```

**Exported YAML:**
```yaml
features:
  - name: user_authentication
    role: Feature Developer
    goal: Implement User Authentication
    branch: feature/user-authentication
    description: |
      Implement JWT auth

      Assigned to: Alice
      Estimated: 16.0 hours
      Tags: auth, security
    expected_output: Complete feature: User Authentication
```

## Tips and Best Practices

### 1. Use Meaningful Titles
- ✅ "Implement JWT authentication with refresh tokens"
- ❌ "Auth stuff"

### 2. Add Detailed Descriptions
Include requirements, acceptance criteria, and technical notes.

### 3. Use Tags Effectively
- Group related items: `["auth", "security"]`
- Mark technical debt: `["tech-debt", "refactor"]`
- Flag urgent items: `["urgent", "hotfix"]`

### 4. Estimate Realistically
Provide estimated hours for better team planning.

### 5. Comment Regularly
Use comments to track progress, decisions, and blockers.

### 6. Keep Teams Organized
Create teams based on your actual team structure or technical areas.

### 7. Use Status Appropriately
Only mark items as "ready" when they have sufficient detail for CLAUDE-9 to work on them.

## Backup and Restore

### Backup
```bash
# Database is just SQLite, copy the file
cp .agent-workspace/work_items.db backups/work_items_$(date +%Y%m%d).db
```

### Restore
```bash
cp backups/work_items_20250101.db .agent-workspace/work_items.db
```

### Export to JSON (for portability)
```python
import sqlite3
import json

conn = sqlite3.connect('.agent-workspace/work_items.db')
conn.row_factory = sqlite3.Row

# Export all work items
cursor = conn.cursor()
cursor.execute('SELECT * FROM work_items')
items = [dict(row) for row in cursor.fetchall()]

with open('work_items_export.json', 'w') as f:
    json.dump(items, f, indent=2)
```

## Troubleshooting

### Database locked error
If you get "database is locked", make sure no other process is accessing the database.

### Work items not exporting
Check the status filter. Only items with `status='ready'` export by default.

### CLI not found
Make sure you're in the orchestrator directory:
```bash
cd claude-multi-agent-orchestrator
python work_item_cli.py --help
```

## Advanced Features

### Custom Metadata
Store any additional data in the metadata field:

```python
manager.create_work_item(
    title="Complex Feature",
    metadata={
        "epic_id": "EPIC-123",
        "sprint": "Sprint 5",
        "story_points": 8,
        "acceptance_criteria": [
            "User can login",
            "Token expires correctly",
            "Refresh works"
        ]
    }
)
```

### Attachments
Track files associated with work items:

```python
# SQL to add attachment
cursor.execute('''
    INSERT INTO attachments (work_item_id, filename, file_path, file_type)
    VALUES (?, ?, ?, ?)
''', (item_id, 'mockup.png', '/path/to/mockup.png', 'image/png'))
```

### Custom Queries
Access the SQLite database directly for custom reporting:

```bash
sqlite3 .agent-workspace/work_items.db

# Get high priority items
SELECT * FROM work_items WHERE priority = 'high' AND status != 'completed';

# Get team workload
SELECT t.name, COUNT(*) as item_count, SUM(wi.estimated_hours) as total_hours
FROM work_items wi
JOIN teams t ON wi.team_id = t.id
WHERE wi.status != 'completed'
GROUP BY t.name;
```

## Next Steps

1. Create your teams
2. Add your work items
3. Mark items as "ready"
4. Export and run with CLAUDE-9
5. Track progress and iterate!

---

**Built for CLAUDE-9 - Multi-Agent Orchestration Powered by Claude**
