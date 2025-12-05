# Test Orchestrator (Dry-Run Mode)

Run the orchestrator in mock mode without consuming API credits.

## What is Dry-Run Mode?

Dry-run mode uses mock LLM responses instead of real Claude API calls:
- No API credits consumed
- Token counts show 66666/0 (alternating marker values)
- Useful for testing orchestration logic and UI
- Git operations still execute normally

## Instructions

### Option 1: Via Dashboard

1. Open Dashboard at http://localhost:3001
2. Navigate to Teams → Select Team
3. Click "Start Run"
4. **Check the "Dry Run" checkbox**
5. Click "Start"

### Option 2: Via API

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "YOUR_TEAM_UUID",
    "work_item_ids": ["WORK_ITEM_UUID"],
    "dry_run": true
  }'
```

### Option 3: Direct CLI

```bash
cd /path/to/target/repo

python /c/projects/claude-9-demo/claude-multi-agent-orchestrator/orchestrator.py \
  --config config.yaml \
  --tasks tasks.yaml \
  --team-id YOUR_TEAM_UUID \
  --dry-run
```

## Force Dry-Run Mode Globally

To force all runs to use dry-run mode:

```bash
# In api/.env
FORCE_DRY_RUN=True

# Restart API
pkill -f uvicorn
cd api && uvicorn app.main:app --reload
```

## Expected Behavior

In dry-run mode you'll see:
- Agents starting and working
- Git worktrees being created
- Mock telemetry with 66666 token markers
- Normal git commits and branch operations
- Successful completion (if logic is correct)

## Use Cases

1. **Testing orchestration logic**: Verify workflow without API costs
2. **UI development**: Test dashboard telemetry display
3. **Debugging git operations**: Isolate git issues from LLM issues
4. **Demo purposes**: Show system capabilities without burning credits
5. **CI/CD testing**: Run tests without real API calls

## Verifying Dry-Run Mode

Check logs for mock telemetry markers:
```bash
grep "66666" .agent-workspace/orchestrator.log
# If found, dry-run mode is active
```

Or check API response:
```bash
curl http://localhost:8000/api/runs/RUN_ID | jq '.dry_run'
# Should return: true
```

## Switching to Real Mode

To run with real LLM calls:

1. Remove `--dry-run` flag from CLI
2. Uncheck "Dry Run" in Dashboard
3. Set `FORCE_DRY_RUN=False` in .env

```bash
# Verify real mode
python orchestrator.py --config config.yaml --tasks tasks.yaml
# Token counts should be realistic numbers, not 66666
```
