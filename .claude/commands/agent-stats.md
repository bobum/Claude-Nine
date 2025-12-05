# Agent Statistics

View performance statistics and metrics from orchestrator runs.

## Quick Stats

### From Database

```bash
cd api

# Total runs by status
sqlite3 claude_nine.db "
SELECT status, COUNT(*) as count
FROM runs
GROUP BY status
ORDER BY count DESC;
"

# Average run duration (completed runs)
sqlite3 claude_nine.db "
SELECT
  AVG((julianday(completed_at) - julianday(started_at)) * 24 * 60) as avg_minutes
FROM runs
WHERE status = 'completed' AND completed_at IS NOT NULL;
"

# Work items by status
sqlite3 claude_nine.db "
SELECT status, COUNT(*) as count
FROM work_items
GROUP BY status
ORDER BY count DESC;
"

# Tasks per run
sqlite3 claude_nine.db "
SELECT
  r.session_id,
  COUNT(rt.id) as task_count,
  r.status
FROM runs r
LEFT JOIN run_tasks rt ON r.id = rt.run_id
GROUP BY r.id
ORDER BY r.created_at DESC
LIMIT 10;
"
```

### From Telemetry Files

```bash
cd /path/to/target/repo

# Run summary
cat .agent-workspace/telemetry/run_summary.json | jq .

# Token usage across all agents
cat .agent-workspace/telemetry/*_events.jsonl | \
  jq -s '[.[] | select(.type == "token_usage")] |
         {total_input: (map(.data.input_tokens) | add),
          total_output: (map(.data.output_tokens) | add)}'

# Git activities count
cat .agent-workspace/telemetry/*_events.jsonl | \
  jq -s '[.[] | select(.type == "git_activity")] | length'
```

## Detailed Analysis

### Token Usage Report

```bash
# Per-agent token usage
for f in .agent-workspace/telemetry/*_latest.json; do
  agent=$(basename "$f" | sed 's/_latest.json//')
  tokens=$(cat "$f" | jq '.token_usage.total_tokens // 0')
  cost=$(cat "$f" | jq '.token_usage.cost_usd // 0')
  echo "$agent: $tokens tokens, \$$cost"
done
```

### Cost Calculation

Claude Sonnet 4.5 pricing:
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

```bash
# Calculate total cost from logs
cat .agent-workspace/orchestrator.log | \
  grep "input_tokens\|output_tokens" | \
  awk '
    /input_tokens/ {input += $NF}
    /output_tokens/ {output += $NF}
    END {
      input_cost = (input / 1000000) * 3.00
      output_cost = (output / 1000000) * 15.00
      printf "Input tokens: %d ($%.2f)\n", input, input_cost
      printf "Output tokens: %d ($%.2f)\n", output, output_cost
      printf "Total cost: $%.2f\n", input_cost + output_cost
    }
  '
```

### Process Metrics

```bash
# CPU and memory usage over time
cat .agent-workspace/telemetry/*_events.jsonl | \
  jq -s '[.[] | select(.type == "process_metrics")] |
         {avg_cpu: (map(.data.cpu_percent) | add / length),
          max_memory_mb: (map(.data.memory_mb) | max),
          avg_memory_mb: (map(.data.memory_mb) | add / length)}'
```

### Git Activity Summary

```bash
# Commits per agent
cat .agent-workspace/telemetry/*_events.jsonl | \
  jq -s 'group_by(.agent_name) |
         map({
           agent: .[0].agent_name,
           commits: [.[] | select(.type == "git_activity" and .data.operation == "commit")] | length
         })'

# Files changed
cat .agent-workspace/telemetry/*_events.jsonl | \
  jq -s '[.[] | select(.type == "git_activity")] |
         map(.data.files_changed) | add'
```

## Historical Statistics

### Query Recent Runs

```bash
sqlite3 api/claude_nine.db "
SELECT
  r.session_id,
  t.name as team,
  r.status,
  datetime(r.created_at) as started,
  datetime(r.completed_at) as completed,
  (SELECT COUNT(*) FROM run_tasks WHERE run_id = r.id) as tasks
FROM runs r
JOIN teams t ON r.team_id = t.id
ORDER BY r.created_at DESC
LIMIT 20;
"
```

### Success Rate

```bash
sqlite3 api/claude_nine.db "
SELECT
  printf('%.1f%%', 100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*)) as success_rate,
  COUNT(*) as total_runs
FROM runs;
"
```

### Average Tasks Per Run

```bash
sqlite3 api/claude_nine.db "
SELECT
  AVG(task_count) as avg_tasks_per_run
FROM (
  SELECT COUNT(*) as task_count
  FROM run_tasks
  GROUP BY run_id
);
"
```

## Export Statistics

### CSV Export

```bash
sqlite3 -header -csv api/claude_nine.db "
SELECT
  r.session_id,
  t.name as team,
  r.status,
  r.created_at,
  r.completed_at,
  (SELECT COUNT(*) FROM run_tasks WHERE run_id = r.id) as tasks
FROM runs r
JOIN teams t ON r.team_id = t.id
ORDER BY r.created_at DESC;
" > run_stats.csv
```

### JSON Export

```bash
sqlite3 api/claude_nine.db "
SELECT json_group_array(json_object(
  'session_id', session_id,
  'status', status,
  'created_at', created_at
))
FROM runs;
" | jq . > run_stats.json
```

## Dashboard Metrics

The Dashboard shows real-time metrics at http://localhost:3001:

- **Team Page**: Active agents, current tasks, token usage
- **Run Details**: Per-task progress, telemetry graphs
- **Work Items**: Status distribution, completion rate

## Visualization Ideas

```bash
# Create simple ASCII chart of run statuses
sqlite3 api/claude_nine.db "
SELECT status, COUNT(*) as count
FROM runs
GROUP BY status;
" | while read line; do
  status=$(echo "$line" | cut -d'|' -f1)
  count=$(echo "$line" | cut -d'|' -f2)
  bar=$(printf '%*s' "$count" | tr ' ' '#')
  printf "%-12s %s (%d)\n" "$status" "$bar" "$count"
done
```
