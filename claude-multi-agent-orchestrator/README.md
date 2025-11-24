# Claude Multi-Agent Orchestrator

A sophisticated multi-agent system using CrewAI and Claude to manage parallel feature development in a monorepo, with intelligent merge conflict resolution using **git worktrees** for true isolation.

## Overview

This orchestrator enables multiple Claude-powered agents to work simultaneously on different features in the same repository, each in their own **isolated workspace**. A dedicated monitor agent continuously watches for potential merge conflicts and intelligently resolves them, ensuring smooth integration of all features.

**Key Innovation**: Uses git worktrees to give each agent its own physical working directory, eliminating conflicts from multiple agents trying to checkout different branches in the same directory.

## Features

- **True Parallel Development**: Each agent works in an isolated git worktree
- **No Directory Conflicts**: Agents never interfere with each other's files
- **Intelligent Conflict Resolution**: Monitor agent detects and resolves merge conflicts automatically
- **Git Integration**: Full git workflow with branching, committing, and merging
- **Atomic Commits**: Agents make incremental, logical commits
- **Automatic Cleanup**: Worktrees are automatically cleaned up on shutdown
- **Production-Ready**: Comprehensive error handling and logging
- **Flexible Configuration**: YAML-based task and configuration management

## Git Worktrees - How It Works

### The Problem
Without worktrees, all agents would share the same working directory:
```
my-project/          # Everyone fights over this directory
├── src/
└── .git/
```

**Result**: Agent 1 checks out `feature/auth`, Agent 2 tries to check out `feature/logging` → **CHAOS** ❌

### The Solution
With worktrees, each agent gets their own isolated directory:
```
my-project/
├── .git/                        # Shared git database
├── src/                         # Main working directory
└── .agent-workspace/
    ├── worktree-auth_system/    # Agent 1's private workspace
    │   └── src/                 # Isolated copy on feature/auth
    ├── worktree-api_logging/    # Agent 2's private workspace
    │   └── src/                 # Isolated copy on feature/logging
    └── worktree-openapi_docs/   # Agent 3's private workspace
        └── src/                 # Isolated copy on feature/docs
```

**Result**: Each agent works independently in their own directory → **TRUE PARALLEL DEVELOPMENT** ✅

### How Worktrees Work

Git worktrees allow multiple working directories from the same repository:
- All worktrees share the same `.git` database
- Each worktree can have a different branch checked out
- Changes in one worktree don't affect others
- Commits from all worktrees appear in the shared repository
- The monitor agent sees all branches and can manage merges

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator                                 │
│  ┌───────────────────────────────────────────────────────┐      │
│  │            CrewAI Parallel Process                     │      │
│  └───────────────────────────────────────────────────────┘      │
│         │                    │                    │              │
│    ┌────▼──────┐       ┌────▼──────┐       ┌────▼──────┐       │
│    │  Agent 1  │       │  Agent 2  │       │  Monitor  │       │
│    │ Feature A │       │ Feature B │       │   Agent   │       │
│    └────┬──────┘       └────┬──────┘       └────┬──────┘       │
│         │                    │                    │              │
│         │                    │                    │              │
└─────────┼────────────────────┼────────────────────┼──────────────┘
          │                    │                    │
     ┌────▼────┐          ┌───▼─────┐         ┌───▼─────┐
     │Worktree │          │Worktree │         │  Main   │
     │ Agent 1 │          │ Agent 2 │         │  Repo   │
     │(isolated)          │(isolated)         │         │
     └────┬────┘          └───┬─────┘         └───┬─────┘
          │                    │                    │
          └────────────────────┴────────────────────┘
                               │
                         ┌─────▼─────┐
                         │  Shared   │
                         │.git Repo  │
                         └───────────┘
```

### Components

1. **Feature Agents**: Each works in an isolated worktree on their own branch
2. **Monitor Agent**: Works in main repo, watches all branches, manages merging
3. **Worktrees**: Isolated working directories, one per feature agent
4. **Git Operations Layer**: Safe, atomic git operations with worktree management
5. **Automatic Cleanup**: Worktrees removed on shutdown or via --cleanup-only flag

## Prerequisites

- Python 3.8 or higher
- Git 2.7+ (for worktree support)
- Anthropic API key
- A git repository (local or cloned)

## Installation

1. **Clone or download this orchestrator:**

```bash
git clone <this-repo>
cd claude-multi-agent-orchestrator
```

2. **Create a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Set up your Anthropic API key

Edit `config.yaml`:

```yaml
anthropic_api_key: "your-api-key-here"
```

Or set as environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 2. Configure settings

Edit `config.yaml` to customize:

```yaml
# Main branch to merge features into
main_branch: "main"

# How often monitor checks for conflicts (seconds)
check_interval: 60

# Enable verbose logging
verbose: true
```

### 3. Define your features

Edit `tasks/example_tasks.yaml` or create your own tasks file:

```yaml
features:
  - name: feature_name
    role: Feature Developer Role
    goal: What this feature accomplishes
    branch: feature/branch-name
    description: |
      Detailed description of what to implement.
      Include specific requirements, file structure,
      and implementation steps.
    expected_output: What the final result should be
```

## Usage

### Basic Usage

Run the orchestrator from your target repository:

```bash
cd /path/to/your-project
python /path/to/orchestrator/orchestrator.py
```

### Advanced Usage

Specify custom config and tasks:

```bash
python orchestrator.py --config my-config.yaml --tasks my-tasks.yaml
```

Run on a different repository:

```bash
python orchestrator.py --repo /path/to/repo
```

### Cleanup Worktrees

If the orchestrator crashes or you need to clean up orphaned worktrees:

```bash
python orchestrator.py --cleanup-only
```

This removes all worktrees in `.agent-workspace/` without running the orchestrator.

### Command-line Options

```
--config CONFIG       Path to configuration file (default: config.yaml)
--tasks TASKS         Path to tasks file (default: tasks/example_tasks.yaml)
--repo REPO           Path to repository (default: current directory)
--cleanup-only        Only clean up existing worktrees and exit
```

## How It Works

### 1. Initialization

- Orchestrator loads configuration and task definitions
- Creates `.agent-workspace/` directory for worktrees and logs
- Initializes main git operations (used by monitor)

### 2. Worktree Creation

For each feature:
1. Creates isolated worktree: `.agent-workspace/worktree-{feature_name}/`
2. Branches from main in that worktree
3. Creates git tools pointing to that specific worktree
4. Agent only sees and modifies files in their worktree

### 3. Parallel Execution

Feature agents work independently in their worktrees:
1. Implement feature step-by-step
2. Make atomic commits for each logical change
3. Push branch after each commit
4. **Never conflict with other agents** - each has their own files!

### 4. Conflict Monitoring

Monitor agent (in main repo) continuously:
1. Lists all feature branches
2. Checks each branch for potential merge conflicts
3. When conflicts detected:
   - Reads both versions from branch history (not worktrees)
   - Analyzes the intent of each change
   - Resolves if changes are compatible
   - Flags for manual review if incompatible
4. Merges conflict-free branches when ready

### 5. Cleanup

On shutdown (normal or Ctrl+C):
- All worktrees are automatically removed
- Git worktree references are pruned
- Only the branches remain (in shared git database)

## Example: Running on an Existing Project

Let's add three features to an Express.js API:

1. **Setup:**

```bash
cd my-express-api
git checkout main
git pull
```

2. **Configure tasks** (`tasks/api-features.yaml`):

```yaml
features:
  - name: auth_system
    branch: feature/auth
    description: |
      Add JWT authentication with:
      - User registration endpoint
      - Login endpoint
      - Auth middleware
      ...

  - name: logging
    branch: feature/logging
    description: |
      Add Winston logging for all requests
      ...

  - name: docs
    branch: feature/docs
    description: |
      Add Swagger documentation
      ...
```

3. **Run orchestrator:**

```bash
python /path/to/orchestrator.py --tasks tasks/api-features.yaml
```

4. **What happens:**

```
my-express-api/
├── .git/
├── src/                          # Your main code (untouched)
└── .agent-workspace/
    ├── worktree-auth_system/     # Agent 1 workspace
    │   └── src/auth/             # Builds auth files here
    ├── worktree-logging/         # Agent 2 workspace
    │   └── src/logging/          # Builds logging files here
    ├── worktree-docs/            # Agent 3 workspace
    │   └── docs/                 # Builds docs files here
    └── orchestrator.log          # All activity logged
```

5. **Monitor progress:**

Watch the logs:
```bash
tail -f .agent-workspace/orchestrator.log
```

6. **Review results:**

All features developed in parallel, conflicts resolved, and merged into main!

## Git Tools Available to Agents

Agents have access to these git operations (scoped to their worktree):

- **Create Branch**: Create new branch (within their worktree)
- **Commit Changes**: Commit all changes with message
- **Write File**: Write content to file (in their worktree)
- **Read File**: Read file from their worktree or any branch
- **Check Conflicts**: Test if branch has merge conflicts
- **Merge Branch**: Merge branch into main (monitor only)
- **Get Branches**: List all branches
- **Get Recent Commits**: View commit history
- **Push Branch**: Push branch to remote
- **Get Current Branch**: Check which branch is active

## Project Structure

```
claude-multi-agent-orchestrator/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── config.yaml           # Configuration (create from template)
├── orchestrator.py       # Main orchestrator logic with worktree support
├── git_operations.py     # Git operations wrapper with worktree methods
├── git_tools.py          # CrewAI tools for git
├── tasks/
│   └── example_tasks.yaml # Example feature definitions
└── .gitignore            # Git ignore patterns
```

When run, creates:
```
your-project/
└── .agent-workspace/               # Orchestrator workspace
    ├── worktree-{feature1}/        # Agent 1 isolated workspace
    │   └── (full working tree)
    ├── worktree-{feature2}/        # Agent 2 isolated workspace
    │   └── (full working tree)
    ├── worktree-{feature3}/        # Agent 3 isolated workspace
    │   └── (full working tree)
    └── orchestrator.log            # Main log file
```

## Best Practices

### Task Definition

- **Be Specific**: Provide detailed requirements and expected file structure
- **Break Down Steps**: List implementation steps in logical order
- **Define Success**: Clearly state what the expected output is
- **Include Tests**: Request tests as part of the feature

### Configuration

- **Adjust Check Interval**: Set based on complexity (30-120 seconds)
- **Use Descriptive Branch Names**: Makes monitoring easier
- **Commit Messages**: Encourage descriptive, conventional commit messages

### Monitoring

- **Watch Logs**: Monitor `.agent-workspace/orchestrator.log` for progress
- **Review Conflicts**: Check how monitor resolves conflicts
- **Manual Review**: Some conflicts may need human intervention
- **Inspect Worktrees**: Can `cd` into worktrees to see agent work in progress

## Troubleshooting

### "Not in a git repository"

Ensure you run the orchestrator from a git repository root:

```bash
cd /path/to/git/repo
python /path/to/orchestrator.py
```

### "API key not found"

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-key"
# Or edit config.yaml
```

### "Worktree already exists"

Clean up orphaned worktrees:

```bash
python orchestrator.py --cleanup-only
```

### "Git worktree command not found"

Update git to version 2.7 or higher:

```bash
git --version
# If < 2.7, update git
```

### Merge conflicts not resolving

Monitor agent may flag conflicts for manual review. Check logs for details and resolve manually:

```bash
git checkout main
git merge feature/branch-name
# Resolve conflicts
git commit
```

### Worktrees not cleaning up

If Ctrl+C or crash leaves worktrees:

```bash
# Manual cleanup
python orchestrator.py --cleanup-only

# Or manually
cd .agent-workspace
rm -rf worktree-*
cd ..
git worktree prune
```

### Agent stuck or not making progress

Check the agent's worktree:

```bash
cd .agent-workspace/worktree-{feature_name}
git status
git log
# See what the agent is doing
```

## Limitations

- Requires git 2.7+ for worktree support
- Requires active Anthropic API key
- Agents work best with clear, structured tasks
- Complex conflicts may still need human review
- Network connection required for API calls
- Git operations require proper permissions
- Worktrees increase disk usage (one copy per agent)

## Advanced Features

### Custom Monitor Logic

Modify `create_monitor_task()` in `orchestrator.py` to customize conflict resolution strategy.

### Additional Tools

Add more tools to `git_tools.py` for specialized operations:
- Code linting
- Test running
- Build verification
- Deployment

### Integration

Integrate with CI/CD by running orchestrator in pipeline:

```yaml
# .github/workflows/multi-agent-dev.yml
- name: Run Multi-Agent Orchestrator
  run: |
    python orchestrator.py --tasks ${{ github.event.inputs.tasks }}
    python orchestrator.py --cleanup-only  # Clean up after
```

### Inspecting Live Progress

While orchestrator runs, inspect worktrees:

```bash
# Terminal 1: Run orchestrator
python orchestrator.py

# Terminal 2: Watch agent 1's work
cd .agent-workspace/worktree-auth_system
watch -n 2 'git log --oneline -5 && echo && git status'

# Terminal 3: Watch agent 2's work
cd .agent-workspace/worktree-api_logging
watch -n 2 'git log --oneline -5 && echo && git status'
```

## Safety Features

- **Isolated Worktrees**: Agents cannot interfere with each other
- **Atomic Operations**: All git operations are atomic and safe
- **Error Handling**: Comprehensive error handling with graceful degradation
- **Automatic Cleanup**: Worktrees automatically removed on shutdown
- **Logging**: Detailed logging of all operations
- **Conflict Detection**: Proactive conflict detection before merging
- **Branch Isolation**: Each feature developed in isolation
- **Rollback**: Git history preserved for easy rollback

## Performance

- **True Parallelism**: Agents work simultaneously without blocking
- **Efficient Worktrees**: Shared .git database minimizes disk usage
- **Minimal Overhead**: Worktrees are lightweight (just file copies)
- **Fast Cleanup**: Worktrees quickly removed on shutdown

## Contributing

To extend the orchestrator:

1. **Add new worktree methods** in `git_operations.py`
2. **Add new tools** in `git_tools.py`
3. **Customize agent behavior** in `orchestrator.py`
4. **Add new task types** in YAML definitions
5. **Test with --cleanup-only** to ensure proper cleanup

## License

This project is provided as-is for educational and development purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `.agent-workspace/orchestrator.log`
3. Try `--cleanup-only` to reset state
4. Check worktree status: `git worktree list`
5. Consult CrewAI documentation
6. Check Anthropic Claude API documentation

---

**Built with:**
- [CrewAI](https://github.com/joaomdmoura/crewAI) - Multi-agent orchestration
- [Claude](https://www.anthropic.com/claude) - AI agents by Anthropic
- [GitPython](https://gitpython.readthedocs.io/) - Git operations
- [Git Worktrees](https://git-scm.com/docs/git-worktree) - Isolated workspaces
- [PyYAML](https://pyyaml.org/) - Configuration management

**Key Innovation**: Git worktrees enable true parallel development by giving each agent an isolated workspace, eliminating the fundamental problem of multiple agents fighting over the same working directory.
