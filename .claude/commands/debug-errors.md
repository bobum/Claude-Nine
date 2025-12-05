# Debug Orchestrator Errors

Analyze and troubleshoot errors from orchestrator runs.

## Log Locations

| Log | Location | Contents |
|-----|----------|----------|
| Orchestrator | `.agent-workspace/orchestrator.log` | Main orchestration events |
| Telemetry | `.agent-workspace/telemetry/*.json` | Agent metrics and events |
| API | `logs/api.log` or stdout | API server logs |
| Dashboard | Browser console | Frontend errors |

## Quick Error Analysis

```bash
cd /path/to/target/repo

# View recent errors
grep -i "error\|exception\|failed" .agent-workspace/orchestrator.log | tail -50

# View with context
grep -B5 -A5 "ERROR" .agent-workspace/orchestrator.log

# View last 100 lines
tail -100 .agent-workspace/orchestrator.log
```

## Common Errors and Solutions

### 1. "Worktree already exists"

**Cause**: Previous run didn't clean up.

**Solution**:
```bash
git worktree list
git worktree remove .agent-workspace/worktree-name --force
git worktree prune
# Or use /cleanup-workspace
```

### 2. "ANTHROPIC_API_KEY not found" / "Authentication failed"

**Cause**: API key not set or invalid.

**Solution**:
```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Set in environment
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Or in .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> api/.env
```

### 3. "Not a git repository"

**Cause**: Running from wrong directory.

**Solution**:
```bash
# Verify you're in a git repo
git status

# Navigate to correct repo
cd /path/to/target/repo
```

### 4. "Rate limit exceeded"

**Cause**: Too many API requests.

**Solution**:
- Wait a few minutes and retry
- Reduce number of parallel agents
- Use dry-run mode for testing: `--dry-run`

### 5. "Merge conflict"

**Cause**: Multiple agents modified same files.

**Solution**:
- Resolver agent should handle automatically
- If not, manually resolve:
```bash
git checkout integration/session-id
git merge feature/branch-name
# Resolve conflicts
git add .
git commit -m "Resolve merge conflicts"
```

### 6. "Connection refused" to API

**Cause**: API server not running.

**Solution**:
```bash
# Check API health
curl http://localhost:8000/health

# If not running, start it
cd api && uvicorn app.main:app --reload
```

### 7. "Database is locked"

**Cause**: SQLite concurrent access issue.

**Solution**:
```bash
# Stop all processes
./stop.sh

# Remove lock file
rm -f api/claude_nine.db-journal

# Restart
./start.sh
```

### 8. "Token usage: 66666"

**Cause**: Running in dry-run/mock mode.

**Note**: This is expected in dry-run mode. The 66666 token count is a marker for mock telemetry.

**Solution** (if you want real execution):
```bash
# Remove --dry-run flag
python orchestrator.py --config config.yaml --tasks tasks.yaml

# Check FORCE_DRY_RUN in .env
grep FORCE_DRY_RUN api/.env
# Should be: FORCE_DRY_RUN=False
```

## Diagnostic Commands

```bash
# Check orchestrator process
ps aux | grep orchestrator

# Check API process
ps aux | grep uvicorn

# Check port usage
lsof -i :8000
lsof -i :3001

# Check git worktree status
git worktree list

# Check branch status
git branch -a

# View recent API logs
tail -100 logs/api.log

# Check database
sqlite3 api/claude_nine.db "SELECT COUNT(*) FROM runs WHERE status='failed';"
```

## Enable Verbose Logging

```bash
# Run orchestrator with verbose output
python orchestrator.py \
  --config config.yaml \
  --tasks tasks.yaml \
  --verbose

# Enable API debug mode
DEBUG=True uvicorn app.main:app --reload
```

## Report Issues

If you can't resolve an error:

1. Collect logs:
   - `.agent-workspace/orchestrator.log`
   - `logs/api.log`
   - Browser console output

2. Note:
   - Exact error message
   - Steps to reproduce
   - Environment (OS, Python version, etc.)

3. Check existing issues or report:
   https://github.com/anthropics/claude-code/issues
