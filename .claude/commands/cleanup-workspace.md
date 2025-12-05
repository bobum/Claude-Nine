# Cleanup Workspace

Remove leftover git worktrees and branches from previous orchestrator runs.

## When to Use

- Before starting a new orchestrator run
- After a run failed or was cancelled
- When you see "worktree already exists" errors
- To clean up disk space

## Instructions

1. **List current worktrees**:
   ```bash
   cd /path/to/target/repo
   git worktree list
   ```

   Expected output if dirty:
   ```
   /path/to/repo                      abc1234 [main]
   /path/to/repo/.agent-workspace/worktree-feature-auth  def5678 [feature/auth]
   /path/to/repo/.agent-workspace/worktree-feature-docs  ghi9012 [feature/docs]
   ```

2. **Remove each worktree**:
   ```bash
   git worktree remove .agent-workspace/worktree-feature-auth --force
   git worktree remove .agent-workspace/worktree-feature-docs --force
   ```

3. **Prune worktree references**:
   ```bash
   git worktree prune
   ```

4. **Delete orphaned branches** (optional):
   ```bash
   # List feature branches
   git branch | grep feature/

   # Delete specific branch
   git branch -D feature/auth
   git branch -D feature/docs

   # Delete integration branches
   git branch | grep integration/ | xargs git branch -D
   ```

5. **Clean up workspace directory**:
   ```bash
   rm -rf .agent-workspace/
   ```

6. **Verify clean state**:
   ```bash
   git worktree list
   # Should only show main worktree
   ```

## Quick Cleanup (Single Command)

Using the orchestrator's built-in cleanup:
```bash
cd /path/to/target/repo
python /c/projects/claude-9-demo/claude-multi-agent-orchestrator/orchestrator.py --cleanup-only
```

## Automated Cleanup Script

```bash
#!/bin/bash
# cleanup-worktrees.sh

REPO_PATH="${1:-.}"
cd "$REPO_PATH"

echo "Current worktrees:"
git worktree list

echo ""
echo "Removing agent worktrees..."
for worktree in $(git worktree list --porcelain | grep "^worktree" | grep ".agent-workspace" | cut -d' ' -f2); do
    echo "Removing: $worktree"
    git worktree remove "$worktree" --force 2>/dev/null || true
done

echo ""
echo "Pruning stale references..."
git worktree prune

echo ""
echo "Removing .agent-workspace directory..."
rm -rf .agent-workspace/

echo ""
echo "Final state:"
git worktree list
```

## What Gets Cleaned

| Item | Location | Description |
|------|----------|-------------|
| Worktrees | `.agent-workspace/worktree-*` | Agent working directories |
| Feature branches | `feature/*` | Agent feature branches |
| Integration branches | `integration/*` | Run integration branches |
| Logs | `.agent-workspace/*.log` | Orchestrator logs |
| Telemetry | `.agent-workspace/telemetry/` | Telemetry JSON files |

## Troubleshooting

- **"worktree is dirty"**: Use `--force` flag
- **"branch is checked out"**: Remove worktree first, then branch
- **Permission denied**: Check file ownership
