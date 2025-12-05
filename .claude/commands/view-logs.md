# View Logs

Stream and analyze logs from Claude-Nine components.

## Log Locations

| Component | Location | Description |
|-----------|----------|-------------|
| Orchestrator | `.agent-workspace/orchestrator.log` | Main orchestration events |
| Telemetry | `.agent-workspace/telemetry/*.json` | Per-agent metrics |
| Run Summary | `.agent-workspace/telemetry/run_summary.json` | Execution statistics |
| API Server | `logs/api.log` or stdout | FastAPI server logs |
| Dashboard | Browser DevTools Console | Frontend errors |

## View Orchestrator Logs

### Stream Live (Follow Mode)

```bash
cd /path/to/target/repo

# Follow log in real-time
tail -f .agent-workspace/orchestrator.log

# Filter for specific agent
tail -f .agent-workspace/orchestrator.log | grep "Agent-1"

# Filter for errors only
tail -f .agent-workspace/orchestrator.log | grep -i "error\|exception"
```

### View Recent Logs

```bash
# Last 100 lines
tail -100 .agent-workspace/orchestrator.log

# Last 50 errors
grep -i "error" .agent-workspace/orchestrator.log | tail -50

# With line numbers
grep -n "ERROR" .agent-workspace/orchestrator.log
```

### Search Logs

```bash
# Find specific content
grep "commit" .agent-workspace/orchestrator.log

# Find with context (5 lines before/after)
grep -B5 -A5 "failed" .agent-workspace/orchestrator.log

# Count occurrences
grep -c "token" .agent-workspace/orchestrator.log
```

## View Telemetry Data

### Latest Agent Status

```bash
# View latest telemetry for specific agent
cat .agent-workspace/telemetry/agent_name_latest.json | jq .

# View all agent statuses
for f in .agent-workspace/telemetry/*_latest.json; do
  echo "=== $f ==="
  cat "$f" | jq .
done
```

### Event Stream

```bash
# View all events (JSONL format)
cat .agent-workspace/telemetry/agent_name_events.jsonl

# Parse with jq
cat .agent-workspace/telemetry/agent_name_events.jsonl | jq -s '.'

# Filter by event type
cat .agent-workspace/telemetry/agent_name_events.jsonl | jq 'select(.type == "git_activity")'
```

### Run Summary

```bash
cat .agent-workspace/telemetry/run_summary.json | jq .
```

Example output:
```json
{
  "session_id": "abc12345",
  "start_time": "2024-12-05T10:00:00Z",
  "end_time": "2024-12-05T10:05:00Z",
  "duration_seconds": 300,
  "total_events": 150,
  "agents": ["Agent-1", "Agent-2"],
  "status": "completed"
}
```

## View API Logs

### If Logging to File

```bash
tail -f logs/api.log
```

### If Logging to stdout

API logs appear in the terminal where uvicorn was started.

### Enable Debug Logging

```bash
DEBUG=True uvicorn app.main:app --reload
```

## View Dashboard Logs

1. Open browser DevTools (F12)
2. Go to Console tab
3. Filter by "error" or "warn"

### Check WebSocket Connection

```javascript
// In browser console
console.log("WebSocket state:", window.ws?.readyState);
// 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED
```

## Log Analysis Commands

### Count Events by Type

```bash
grep -o '"type":"[^"]*"' .agent-workspace/telemetry/*.jsonl | \
  sort | uniq -c | sort -rn
```

### Find Slowest Operations

```bash
grep "duration" .agent-workspace/orchestrator.log | \
  sort -t: -k2 -rn | head -10
```

### Token Usage Summary

```bash
grep "token" .agent-workspace/orchestrator.log | \
  grep -o "tokens: [0-9]*" | \
  awk -F: '{sum+=$2} END {print "Total tokens:", sum}'
```

### Error Timeline

```bash
grep -i "error" .agent-workspace/orchestrator.log | \
  cut -d' ' -f1-2 | sort | uniq -c
```

## Clear Old Logs

```bash
# Remove orchestrator log
rm .agent-workspace/orchestrator.log

# Remove all telemetry
rm -rf .agent-workspace/telemetry/

# Remove API logs
rm -rf logs/*.log
```

## Log Rotation

For production, consider log rotation:

```bash
# Using logrotate (Linux)
cat > /etc/logrotate.d/claude-nine << EOF
/path/to/.agent-workspace/orchestrator.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF
```
