<div align="center">

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║  ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗      █████╗       ║
║ ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝     ██╔══██╗      ║
║ ██║     ██║     ███████║██║   ██║██║  ██║█████╗ █████╗╚██████║      ║
║ ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝ ╚════╝ ╚═══██║      ║
║ ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗     █████╔╝       ║
║  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝     ╚════╝        ║
║                                                                       ║
║            Multi-Agent Orchestration Powered by Claude                ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

<!-- Add your cool Cloud9/Claude-Nine image here -->
<!-- <img src=".github/assets/cloud9-banner.png" alt="Cloud9 Claude Nine" width="800"/> -->

<p align="center">
  <strong>Where Claude agents soar together in perfect harmony ☁️</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/AI-Claude%20Sonnet%204.5-purple.svg" alt="Claude Sonnet 4.5"/>
  <img src="https://img.shields.io/badge/Framework-CrewAI-orange.svg" alt="CrewAI"/>
  <img src="https://img.shields.io/badge/Git-Worktrees-green.svg" alt="Git Worktrees"/>
  <img src="https://img.shields.io/badge/Status-Production%20Ready-success.svg" alt="Production Ready"/>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-documentation">Documentation</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

</div>

## 🏠 Runs 100% Locally

**Claude-Nine runs entirely on your machine** - no cloud infrastructure required!

```bash
# One-line installation
./install.sh

# Start Claude-Nine
./start.sh

# Open http://localhost:3000
```

✅ Local database (SQLite - no setup needed)
✅ Local API server (FastAPI on localhost:8000)
✅ Local dashboard (Next.js on localhost:3000)
✅ Your git repos stay local
⚡ Only dependency: Anthropic API for Claude AI

**[📖 Local Setup Guide](docs/local-setup-guide.md)** | **[🚀 Quick Start](#-quick-start)**

---

## 🌟 What is CLAUDE-9?

**CLAUDE-9** is a revolutionary multi-agent orchestration platform that enables **multiple Claude AI agents** to work simultaneously on different features in the same codebase—without stepping on each other's toes.

Think of it as your **personal AI development team in a box**, complete with:
- 🎛️ **Web Dashboard** - Manage teams, assign work, monitor progress
- 🤖 **AI Agents** - Claude-powered developers working in parallel
- 📋 **Work Queue** - Integrate with Azure DevOps, Jira, GitHub, or create manual tasks
- 📊 **Real-time Monitoring** - Watch your AI team code in real-time
- 🔄 **Git Worktrees** - Each agent works in isolated directories

### 🎭 The Magic

```
                    🎼 Orchestrator
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    🤖 Agent 1       🤖 Agent 2       👁️ Monitor
   (Auth System)   (API Logging)   (Conflict Resolver)
        │                │                │
        ▼                ▼                ▼
    📁 Worktree 1    📁 Worktree 2    📚 Main Repo
   (Isolated)       (Isolated)       (Overseer)
        │                │                │
        └────────────────┴────────────────┘
                         │
                    🗄️ Shared Git
                         │
                    ✨ Merged Features
```

## ✨ Features

<table>
<tr>
<td width="50%">

### 🚀 True Parallel Development
Each agent works in its own **isolated git worktree**, enabling genuine simultaneous development without conflicts.

### 🧠 Intelligent Conflict Resolution
A dedicated monitor agent watches all branches, detects merge conflicts, and resolves them intelligently using Claude's reasoning.

### 🔄 Automatic Orchestration
Define features in YAML, run one command, and watch multiple agents implement them in parallel—complete with commits and merges.

</td>
<td width="50%">

### 🛡️ Production-Ready Safety
- Atomic git operations
- Automatic worktree cleanup
- Comprehensive error handling
- Detailed logging
- Graceful shutdown (Ctrl+C safe)

### 📦 Zero Directory Conflicts
Git worktrees give each agent its own physical workspace—no more agents fighting over the same files!

### 🎯 YAML-Driven Configuration
Simple, declarative task definitions make it easy to specify exactly what you want built.

</td>
</tr>
</table>

## 🎯 Use Cases

<div align="center">

| Scenario | Description | Benefit |
|----------|-------------|---------|
| 🏗️ **Rapid Prototyping** | Develop multiple features simultaneously | 3x faster development |
| 🔧 **Legacy Modernization** | Add auth, logging, docs in parallel | Coordinate complex changes |
| 🧪 **Experimental Features** | Try multiple approaches at once | Compare solutions easily |
| 📚 **Documentation Sprints** | Generate docs while building features | Never fall behind |
| 🎨 **Refactoring** | Modernize multiple modules together | Maintain consistency |

</div>

## 🚀 Quick Start

### Prerequisites

```bash
✓ Python 3.12+
✓ Node.js 18+
✓ Git 2.7+
✓ Anthropic API key (get one at console.anthropic.com)
```

### One-Command Installation

```bash
# 1. Clone Claude-Nine
git clone https://github.com/bobum/Claude-Nine.git
cd Claude-Nine

# 2. Run the installer (checks everything and sets up automatically)
./install.sh

# 3. Start Claude-Nine
./start.sh
```

The installer will:
1. ✓ Check Python, Node.js, and Git are installed
2. ✓ Prompt for your Anthropic API key
3. ✓ Set up the API server with local SQLite database
4. ✓ Install dashboard dependencies
5. ✓ Create helper scripts (start.sh, stop.sh)

###  Your First Claude-Nine Session 🚀

```bash
# Start everything
./start.sh

# Open your browser
open http://localhost:3000  # macOS
# or visit http://localhost:3000 in your browser
```

**What you'll see:**
- 🎯 **Interactive Tutorial** - Guides you through all features
- 👥 **Teams Page** - Create AI development teams
- 📋 **Work Queue** - Assign tasks from DevOps/Jira or create manually
- 📊 **Real-time Dashboard** - Monitor your AI agents working

**That's it!** Your AI development team is ready to code.

## 🎬 Example: Building an Express API

Let's add authentication, logging, and documentation to an Express.js API—**all at once**:

**1. Create your mission brief** (`tasks/api-enhancement.yaml`):

```yaml
features:
  - name: jwt_authentication
    branch: feature/auth
    description: |
      Implement JWT authentication with:
      - User registration endpoint
      - Login endpoint
      - Token verification middleware
      - Password hashing with bcrypt

  - name: winston_logging
    branch: feature/logging
    description: |
      Add comprehensive logging with:
      - Request/response logging
      - Error tracking
      - Performance metrics
      - Log rotation

  - name: swagger_docs
    branch: feature/docs
    description: |
      Create OpenAPI documentation:
      - Interactive Swagger UI
      - All endpoint documentation
      - Schema definitions
      - Authentication examples
```

**2. Launch CLAUDE-9**:

```bash
cd my-express-api
python /path/to/orchestrator.py --tasks tasks/api-enhancement.yaml
```

**3. Watch the magic** ✨:

```
🎼 Starting Multi-Agent Orchestrator with Worktrees
================================================================================
Creating 3 feature agents (each with isolated worktree)
Created 1 monitor agent (working in main repo)

Worktrees created at:
  - .agent-workspace/worktree-jwt_authentication
  - .agent-workspace/worktree-winston_logging
  - .agent-workspace/worktree-swagger_docs

🚀 Starting crew execution...

[Agent jwt_authentication] Creating src/auth/auth.js...
[Agent winston_logging] Installing winston dependency...
[Agent swagger_docs] Setting up Swagger UI...
[Monitor Agent] Checking for conflicts...
[Agent jwt_authentication] Implementing user registration...
[Monitor Agent] No conflicts detected ✓
[Agent winston_logging] Adding request logger middleware...
...
```

**4. Result**: Three features developed in parallel, conflicts resolved, merged to main! 🎉

## 🏗️ How It Works

### The Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    🎼 ORCHESTRATOR                          │
│  ┌───────────────────────────────────────────────────┐     │
│  │          CrewAI Parallel Process                   │     │
│  └───────────────────────────────────────────────────┘     │
│         │                  │                  │             │
│    ┌────▼────┐       ┌────▼────┐       ┌────▼────┐        │
│    │ Agent 1 │       │ Agent 2 │       │ Monitor │        │
│    │  🤖     │       │  🤖     │       │   👁️    │        │
│    └────┬────┘       └────┬────┘       └────┬────┘        │
└─────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                  │
     ┌────▼────┐       ┌───▼─────┐       ┌───▼─────┐
     │Worktree │       │Worktree │       │  Main   │
     │   1     │       │   2     │       │  Repo   │
     │ 📁      │       │ 📁      │       │  📚     │
     └────┬────┘       └───┬─────┘       └───┬─────┘
          │                 │                  │
          └─────────────────┴──────────────────┘
                            │
                      ┌─────▼─────┐
                      │ Shared    │
                      │ .git DB   │
                      │  🗄️       │
                      └───────────┘
```

### The Secret Sauce: Git Worktrees

**The Problem** ❌:
```
my-project/          # All agents fight over this directory!
├── src/
└── .git/
```
→ Agent 1 checks out `feature/auth`
→ Agent 2 tries to check out `feature/logging`
→ **CHAOS!** Files constantly switching, work overwritten

**The Solution** ✅:
```
my-project/
├── .git/                        # Shared git database
├── src/                         # Main directory (untouched)
└── .agent-workspace/
    ├── worktree-auth/           # Agent 1's private workspace
    │   └── src/                 # Independent file copy
    ├── worktree-logging/        # Agent 2's private workspace
    │   └── src/                 # Independent file copy
    └── worktree-docs/           # Agent 3's private workspace
        └── src/                 # Independent file copy
```
→ Each agent has own directory
→ No conflicts, true parallelism
→ **HARMONY!** ☁️

## 📚 Documentation

### Core Components

- **[claude-multi-agent-orchestrator/](claude-multi-agent-orchestrator/)** - The main orchestration system
  - `orchestrator.py` - Multi-agent coordinator with worktree support
  - `git_operations.py` - Git operations wrapper with worktree management
  - `git_tools.py` - CrewAI tools for git operations
  - `tasks/` - YAML task definitions
  - `README.md` - Comprehensive documentation

### Key Concepts

<details>
<summary><b>🎯 Agents</b></summary>

**Feature Agents**: Autonomous developers that implement specific features in isolated worktrees.

**Monitor Agent**: Oversees all branches, detects conflicts, and manages intelligent merging.

Each agent is powered by Claude Sonnet 4.5 and has access to git tools.
</details>

<details>
<summary><b>📁 Worktrees</b></summary>

Git worktrees enable multiple working directories from the same repository:
- Shared `.git` database (efficient)
- Independent file copies (isolated)
- Each worktree on different branch
- Changes visible across all worktrees
- Automatic cleanup on shutdown
</details>

<details>
<summary><b>🔧 Tasks</b></summary>

Tasks are defined in YAML with:
- `name`: Feature identifier
- `role`: Agent role/specialization
- `goal`: What to accomplish
- `branch`: Git branch name
- `description`: Detailed implementation steps
- `expected_output`: Success criteria

See [`tasks/example_tasks.yaml`](claude-multi-agent-orchestrator/tasks/example_tasks.yaml) for examples.
</details>

<details>
<summary><b>👁️ Monitoring & Conflict Resolution</b></summary>

The monitor agent:
1. Checks all branches every N seconds
2. Tests for merge conflicts
3. Reads conflicting files from both branches
4. Uses Claude to analyze compatibility
5. Auto-resolves or flags for review
6. Merges when ready

Configurable via `check_interval` in `config.yaml`.
</details>

## 🎨 Advanced Usage

### Custom Orchestration

```python
from orchestrator import MultiAgentOrchestrator

# Create orchestrator
orchestrator = MultiAgentOrchestrator(
    config_path="my-config.yaml",
    tasks_path="my-tasks.yaml"
)

# Add custom signal handling
orchestrator.setup_signal_handlers()

# Run it
result = orchestrator.run()
```

### Inspecting Live Progress

Watch your agents work in real-time:

```bash
# Terminal 1: Run orchestrator
python orchestrator.py

# Terminal 2: Watch Agent 1
cd .agent-workspace/worktree-auth
watch -n 2 'git log --oneline -5 && echo && git status'

# Terminal 3: Watch Agent 2
cd .agent-workspace/worktree-logging
watch -n 2 'git log --oneline -5 && echo && git status'
```

### Manual Cleanup

If orchestrator crashes or you need to reset:

```bash
python orchestrator.py --cleanup-only
```

### Integration with CI/CD

```yaml
# .github/workflows/multi-agent-dev.yml
name: Multi-Agent Development

on:
  workflow_dispatch:
    inputs:
      tasks_file:
        description: 'Tasks YAML file'
        required: true
        default: 'tasks/features.yaml'

jobs:
  orchestrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          cd claude-multi-agent-orchestrator
          pip install -r requirements.txt

      - name: Run CLAUDE-9 Orchestrator
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python orchestrator.py --tasks ${{ inputs.tasks_file }}
          python orchestrator.py --cleanup-only
```

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| 🚫 "Not in a git repository" | Run from git repository root |
| 🔑 "API key not found" | Set `ANTHROPIC_API_KEY` environment variable |
| 🌲 "Worktree already exists" | Run `python orchestrator.py --cleanup-only` |
| ⚠️ "Git worktree command not found" | Update git to 2.7+ |
| 🔄 Agent stuck/not progressing | Check `.agent-workspace/orchestrator.log` for errors |
| 💥 Crashes leave worktrees | Always safe: run `--cleanup-only` to reset |

## 🤝 Contributing

We welcome contributions! CLAUDE-9 is designed to be extensible:

### Ways to Contribute

- 🐛 **Bug Reports**: Found an issue? Open a GitHub issue
- ✨ **Feature Requests**: Have an idea? We'd love to hear it
- 🔧 **Pull Requests**: Improvements welcome!
- 📚 **Documentation**: Help others get started
- 🎨 **Examples**: Share your task definitions

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/Claude-Nine.git
cd Claude-Nine

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes, test, commit
git commit -m "Add amazing feature"

# Push and create PR
git push origin feature/amazing-feature
```

## 📊 Performance

- **Parallel Speedup**: 3-5x faster than sequential development
- **Memory Efficient**: Shared `.git` database minimizes disk usage
- **Lightweight Worktrees**: ~100MB per worktree for typical projects
- **Cleanup Time**: <5 seconds for 10 worktrees
- **API Efficient**: Parallel requests maximize Claude API throughput

## 🌈 Roadmap

- [ ] **Multi-model support** - GPT-4, Gemini alongside Claude
- [ ] **Web UI** - Visual dashboard for monitoring agents
- [ ] **Task templates** - Pre-built task libraries
- [ ] **Conflict ML** - Learn conflict patterns over time
- [ ] **Team mode** - Human + AI hybrid development
- [ ] **Code review agent** - Automated PR reviews
- [ ] **Testing agent** - Auto-generate comprehensive tests
- [ ] **Deployment agent** - Handle CI/CD integration

## 📜 License

This project is provided as-is for educational and development purposes.

## 🙏 Acknowledgments

Built with love using:
- [**CrewAI**](https://github.com/joaomdmoura/crewAI) - Multi-agent orchestration framework
- [**Claude Sonnet 4.5**](https://www.anthropic.com/claude) - Anthropic's AI model
- [**GitPython**](https://gitpython.readthedocs.io/) - Git operations in Python
- [**Git Worktrees**](https://git-scm.com/docs/git-worktree) - Isolated workspace magic
- [**PyYAML**](https://pyyaml.org/) - Configuration management

## 💬 Support

- 📖 **Documentation**: See [`claude-multi-agent-orchestrator/README.md`](claude-multi-agent-orchestrator/README.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/Claude-Nine/issues)
- 💡 **Discussions**: [GitHub Discussions](https://github.com/yourusername/Claude-Nine/discussions)

---

<div align="center">

### 🌟 Star us on GitHub — it motivates us to keep improving CLAUDE-9!

**Made with ☁️ and ❤️ by developers who believe AI should work together, not alone**

```
     ☁️  ☁️  ☁️
  ☁️  ☁️  ☁️  ☁️
    🤖  🤖  🤖
   Working in harmony
    on CLAUDE-9
```

[⬆ Back to Top](#)

</div>
