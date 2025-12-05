# Run Orchestrator

Execute the multi-agent orchestrator to process work items.

## Prerequisites

Before running:
1. API server must be running (http://localhost:8000/health)
2. ANTHROPIC_API_KEY must be set
3. Target repository must be a valid git repo
4. No leftover worktrees from previous runs (use `/cleanup-workspace` if needed)

## Instructions

### Option 1: Via Dashboard (Recommended)

1. Open Dashboard at http://localhost:3001
2. Navigate to Teams
3. Select a team with queued work items
4. Click "Start Run"
5. Monitor progress in real-time

### Option 2: Via API

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "YOUR_TEAM_UUID",
    "work_item_ids": ["WORK_ITEM_UUID_1", "WORK_ITEM_UUID_2"],
    "dry_run": false
  }'
```

### Option 3: Direct CLI (for testing/debugging)

```bash
cd /path/to/target/repo  # Must be a git repository

# Normal mode (uses API credits)
python /c/projects/claude-9-demo/claude-multi-agent-orchestrator/orchestrator.py \
  --config config.yaml \
  --tasks tasks.yaml \
  --team-id YOUR_TEAM_UUID

# Dry-run mode (mock LLM, no API credits)
python /c/projects/claude-9-demo/claude-multi-agent-orchestrator/orchestrator.py \
  --config config.yaml \
  --tasks tasks.yaml \
  --team-id YOUR_TEAM_UUID \
  --dry-run
```

## Task File Format

Create a tasks YAML file:
```yaml
features:
  - name: feature-name
    branch: feature/branch-name
    work_item_id: "uuid-here"
    external_id: "TASK-123"
    role: "Senior Software Developer"
    goal: "Implement the feature"
    description: |
      Detailed description of what to implement...
    expected_output: "Complete implementation with tests"
```

## What Happens

1. **Session Setup**: Creates integration branch and session ID
2. **Agent Creation**: Spawns N agents with isolated git worktrees
3. **Parallel Execution**: All agents work simultaneously
4. **Telemetry**: Progress streamed to Dashboard in real-time
5. **Post-Completion**: All feature branches merged into integration branch
6. **Cleanup**: Worktrees removed after completion

## Monitor Progress

- **Dashboard**: Real-time telemetry on team page
- **Logs**: `.agent-workspace/orchestrator.log`
- **API**: `GET /api/runs/{run_id}` for status

## Troubleshooting

- **"Worktree already exists"**: Run `/cleanup-workspace` first
- **"API key not found"**: Set ANTHROPIC_API_KEY in environment
- **"Not a git repository"**: cd to valid git repo before running
- **Agents failing**: Check orchestrator.log for errors
