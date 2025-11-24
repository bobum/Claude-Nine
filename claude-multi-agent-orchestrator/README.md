# Claude Multi-Agent Orchestrator

A sophisticated multi-agent system using CrewAI and Claude to manage parallel feature development in a monorepo, with intelligent merge conflict resolution.

## Overview

This orchestrator enables multiple Claude-powered agents to work simultaneously on different features in the same repository, each on their own git branch. A dedicated monitor agent continuously watches for potential merge conflicts and intelligently resolves them, ensuring smooth integration of all features.

## Features

- **Parallel Development**: Multiple agents work on different features simultaneously
- **Intelligent Conflict Resolution**: Monitor agent detects and resolves merge conflicts automatically
- **Git Integration**: Full git workflow with branching, committing, and merging
- **Atomic Commits**: Agents make incremental, logical commits
- **Production-Ready**: Comprehensive error handling and logging
- **Flexible Configuration**: YAML-based task and configuration management

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │              CrewAI Parallel Process             │   │
│  └─────────────────────────────────────────────────┘   │
│         │              │              │                 │
│    ┌────▼────┐    ┌───▼────┐    ┌───▼────┐           │
│    │ Agent 1 │    │ Agent 2│    │Monitor │           │
│    │Feature A│    │Feature B    │ Agent  │           │
│    └────┬────┘    └───┬────┘    └───┬────┘           │
│         │             │              │                 │
└─────────┼─────────────┼──────────────┼─────────────────┘
          │             │              │
     ┌────▼─────────────▼──────────────▼────┐
     │         Git Operations Layer          │
     │  (GitPython + Custom Tools)           │
     └────┬──────────────────────────────────┘
          │
     ┌────▼────┐
     │   Git   │
     │  Repo   │
     └─────────┘
```

### Components

1. **Feature Agents**: Independent agents that develop specific features on their own branches
2. **Monitor Agent**: Watches all branches, detects conflicts, and manages merging
3. **Git Operations Layer**: Safe, atomic git operations wrapper
4. **CrewAI Tools**: Git operations exposed as tools for agent use

## Prerequisites

- Python 3.8 or higher
- Git installed and configured
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

### Command-line Options

```
--config CONFIG   Path to configuration file (default: config.yaml)
--tasks TASKS     Path to tasks file (default: tasks/example_tasks.yaml)
--repo REPO       Path to repository (default: current directory)
```

## How It Works

### 1. Initialization

- Orchestrator loads configuration and task definitions
- Creates a CrewAI agent for each feature
- Creates a monitor agent for conflict resolution
- Initializes git tools for all agents

### 2. Parallel Execution

Feature agents work independently:
1. Create a new branch from main
2. Implement the feature step-by-step
3. Make atomic commits for each logical change
4. Push branch after each commit

### 3. Conflict Monitoring

Monitor agent continuously:
1. Lists all feature branches
2. Checks each branch for potential merge conflicts
3. When conflicts detected:
   - Reads both versions of conflicting files
   - Analyzes the intent of each change
   - Resolves if changes are compatible
   - Flags for manual review if incompatible
4. Merges conflict-free branches when ready

### 4. Completion

- All features are developed and merged
- Final state is logged
- Summary report is generated

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

4. **Monitor progress:**

Watch the logs in `.agent-workspace/orchestrator.log` or the console output.

5. **Review results:**

All features will be developed in parallel, conflicts resolved, and merged into main.

## Git Tools Available to Agents

Agents have access to these git operations:

- **Create Branch**: Create new branch from main
- **Commit Changes**: Commit all changes with message
- **Write File**: Write content to file
- **Read File**: Read file from working directory or specific branch
- **Check Conflicts**: Test if branch has merge conflicts
- **Merge Branch**: Merge branch into main
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
├── orchestrator.py       # Main orchestrator logic
├── git_operations.py     # Git operations wrapper
├── git_tools.py          # CrewAI tools for git
├── tasks/
│   └── example_tasks.yaml # Example feature definitions
└── .gitignore            # Git ignore patterns
```

When run, creates:
```
your-project/
└── .agent-workspace/      # Orchestrator workspace
    ├── orchestrator.log   # Main log file
    └── ...                # Agent state files
```

## Best Practices

### Task Definition

- **Be Specific**: Provide detailed requirements and expected file structure
- **Break Down Steps**: List implementation steps in logical order
- **Define Success**: Clearly state what the expected output is
- **Include Tests**: Request tests as part of the feature

### Configuration

- **Adjust Check Interval**: Set based on complexity (30-120 seconds)
- **Use Branches**: Always work on feature branches, never directly on main
- **Commit Messages**: Encourage descriptive, conventional commit messages

### Monitoring

- **Watch Logs**: Monitor `.agent-workspace/orchestrator.log` for progress
- **Review Conflicts**: Check how monitor resolves conflicts
- **Manual Review**: Some conflicts may need human intervention

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

### "Branch already exists"

The orchestrator will checkout existing branches. To start fresh:

```bash
git branch -D feature/branch-name
```

### Merge conflicts not resolving

Monitor agent may flag conflicts for manual review. Check logs for details and resolve manually:

```bash
git checkout main
git merge feature/branch-name
# Resolve conflicts
git commit
```

## Limitations

- Requires active Anthropic API key
- Agents work best with clear, structured tasks
- Complex conflicts may still need human review
- Network connection required for API calls
- Git operations require proper permissions

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
  run: python orchestrator.py --tasks ${{ github.event.inputs.tasks }}
```

## Safety Features

- **Atomic Operations**: All git operations are atomic and safe
- **Error Handling**: Comprehensive error handling with graceful degradation
- **Logging**: Detailed logging of all operations
- **Conflict Detection**: Proactive conflict detection before merging
- **Branch Isolation**: Each feature developed in isolation
- **Rollback**: Git history preserved for easy rollback

## Performance

- Parallel execution reduces total development time
- Multiple agents work simultaneously
- Monitor runs asynchronously
- Efficient git operations with minimal overhead

## Contributing

To extend the orchestrator:

1. Add new tools in `git_tools.py`
2. Extend `GitOperations` class for new git operations
3. Customize agent behavior in `orchestrator.py`
4. Add new task types in YAML definitions

## License

This project is provided as-is for educational and development purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `.agent-workspace/`
3. Consult CrewAI documentation
4. Check Anthropic Claude API documentation

---

**Built with:**
- [CrewAI](https://github.com/joaomdmoura/crewAI) - Multi-agent orchestration
- [Claude](https://www.anthropic.com/claude) - AI agents by Anthropic
- [GitPython](https://gitpython.readthedocs.io/) - Git operations
- [PyYAML](https://pyyaml.org/) - Configuration management
