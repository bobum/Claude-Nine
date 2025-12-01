# Claude-Nine Local Setup Guide

Complete guide for running Claude-Nine entirely on your local machine. No cloud infrastructure required.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Automated Installation](#automated-installation)
4. [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
6. [Running Claude-Nine](#running-claude-nine)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

---

## Overview

Claude-Nine runs completely on your local machine:
- **API Server**: FastAPI running on localhost:8000
- **Dashboard**: Next.js running on localhost:3000
- **Database**: SQLite file (no separate database server needed)
- **AI**: Anthropic Claude API (only cloud dependency)

**Storage Location**: Everything lives in your Claude-Nine directory
- Database: `api/claude_nine.db`
- Configuration: `api/.env`
- Agent workspaces: `.agent-workspace/` (created when teams run)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Check Command | Download |
|----------|----------------|---------------|----------|
| **Python** | 3.12+ | `python3 --version` | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | `node --version` | [nodejs.org](https://nodejs.org/) |
| **npm** | 8+ | `npm --version` | (included with Node.js) |
| **Git** | 2.7+ | `git --version` | [git-scm.com](https://git-scm.com/) |

### Required Account

- **Anthropic API Key**: Sign up at [console.anthropic.com](https://console.anthropic.com/)
  - Free tier available for testing
  - Pay-as-you-go for production use
  - Store your key securely

### System Requirements

- **OS**: Linux, macOS, or Windows (WSL recommended for Windows)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 500MB for software + space for your databases
- **Network**: Internet connection for Claude API calls

---

## Automated Installation

The easiest way to get started:

### Step 1: Clone Repository

```bash
git clone https://github.com/bobum/Claude-Nine.git
cd Claude-Nine
```

### Step 2: Run Installer

```bash
./install.sh
```

The installer will:
1. ✓ Check all prerequisites
2. ✓ Prompt for your Anthropic API key
3. ✓ Set up the API server with SQLite
4. ✓ Install dashboard dependencies
5. ✓ Create helper scripts (`start.sh`, `stop.sh`)
6. ✓ Generate getting started guide

### Step 3: Start Claude-Nine

```bash
./start.sh
```

### Step 4: Open Dashboard

Visit http://localhost:3000 and follow the interactive tutorial!

---

## Manual Installation

If you prefer manual setup or the automated installer fails:

### 1. Set Up API Server

```bash
cd api

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./claude_nine.db
ANTHROPIC_API_KEY=your-actual-api-key-here
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
EOF

# Edit .env to add your API key
nano .env
```

### 2. Set Up Dashboard

```bash
cd dashboard

# Install dependencies
npm install

# (Optional) Create .env.local for custom config
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 3. Create Start Scripts

Create `start-api.sh`:
```bash
#!/bin/bash
cd api
source venv/bin/activate  # If using venv
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Create `start-dashboard.sh`:
```bash
#!/bin/bash
cd dashboard
npm run dev
```

Make them executable:
```bash
chmod +x start-api.sh start-dashboard.sh
```

---

## Configuration

### API Configuration (`api/.env`)

```bash
# Database Location (SQLite)
DATABASE_URL=sqlite:///./claude_nine.db

# Anthropic API Key (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-...your-key-here

# Server Settings
API_HOST=0.0.0.0        # Listen on all interfaces
API_PORT=8000           # API port
DEBUG=True              # Enable debug mode for development
```

### Dashboard Configuration (`dashboard/.env.local`)

Optional - only if you change API port:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Database Configuration

Claude-Nine uses SQLite by default - perfect for local use:

**SQLite (Default)**:
```bash
DATABASE_URL=sqlite:///./claude_nine.db
```
- ✓ Zero setup required
- ✓ Single file database
- ✓ Perfect for 1-10 teams
- ✓ Easy to backup (just copy the file)

**Local PostgreSQL (Optional)**:
```bash
DATABASE_URL=postgresql://localhost:5432/claude_nine
```
- Better for 10+ concurrent teams
- Requires PostgreSQL installed locally
- Better performance at scale

---

## Running Claude-Nine

### Option 1: Using Helper Scripts (Recommended)

```bash
# Start everything
./start.sh

# Stop everything
./stop.sh
```

### Option 2: Start Services Separately

**Terminal 1 - API Server**:
```bash
cd api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Dashboard**:
```bash
cd dashboard
npm run dev
```

### Option 3: Background Process

```bash
# Start API in background
cd api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd ..

# Start Dashboard in background
cd dashboard
npm run dev &
cd ..

# View logs
tail -f api/logs/app.log  # If logging is configured
```

### Accessing Claude-Nine

Once started, access:
- **Dashboard**: http://localhost:3000
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

---

## Troubleshooting

### API Won't Start

**Problem**: Port 8000 already in use

```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port in api/.env:
API_PORT=8001
```

**Problem**: API key not set

```bash
# Check api/.env has valid key
cat api/.env | grep ANTHROPIC_API_KEY

# Update if needed
nano api/.env
```

**Problem**: Missing dependencies

```bash
cd api
pip install -r requirements.txt
```

### Dashboard Won't Start

**Problem**: Port 3000 already in use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

**Problem**: Node modules issues

```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
```

**Problem**: Cannot connect to API

```bash
# Check API is running
curl http://localhost:8000/health

# Should return: {"status":"ok","version":"1.0.0","service":"claude-nine-api"}
```

### Database Issues

**Problem**: Database locked

```bash
# Stop all processes
./stop.sh

# Delete and recreate database
rm api/claude_nine.db
cd api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Database will be auto-created
```

**Problem**: Want to reset database

```bash
# Backup first
cp api/claude_nine.db api/claude_nine.db.backup

# Delete to start fresh
rm api/claude_nine.db

# Restart API to recreate
cd api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Tutorial Not Showing

**Problem**: Tutorial completed but want to see it again

- Click the `?` icon in the dashboard header
- Click "Restart Tutorial"
- Refresh the page

**Problem**: Tutorial disabled

- Click the `?` icon in the dashboard header
- Toggle "Enable Tutorial" to ON

---

## Advanced Configuration

### Using Local PostgreSQL

If you want to use PostgreSQL instead of SQLite:

```bash
# Install PostgreSQL
# macOS: brew install postgresql
# Ubuntu: sudo apt install postgresql

# Start PostgreSQL
# macOS: brew services start postgresql
# Ubuntu: sudo systemctl start postgresql

# Create database
createdb claude_nine

# Update api/.env
DATABASE_URL=postgresql://localhost:5432/claude_nine
```

### Running on Different Ports

**API on different port**:
```bash
# api/.env
API_PORT=9000

# dashboard/.env.local
NEXT_PUBLIC_API_URL=http://localhost:9000
```

**Dashboard on different port**:
```bash
# dashboard/package.json
# Change "dev" script to:
"dev": "next dev -p 3001"
```

### Production Build

For better performance in production:

```bash
# API (use gunicorn)
cd api
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Dashboard (build static)
cd dashboard
npm run build
npm start
```

### Running as System Service

**API Service (systemd)**:
```bash
# /etc/systemd/system/claude-nine-api.service
[Unit]
Description=Claude-Nine API
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/Claude-Nine/api
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable claude-nine-api
sudo systemctl start claude-nine-api
```

### Backup and Restore

**Backup your data**:
```bash
# Backup database
cp api/claude_nine.db backups/claude_nine_$(date +%Y%m%d).db

# Backup configuration
cp api/.env backups/.env_$(date +%Y%m%d)
```

**Restore from backup**:
```bash
# Stop services
./stop.sh

# Restore database
cp backups/claude_nine_20241125.db api/claude_nine.db

# Restart
./start.sh
```

### Using Docker (Optional)

For containerized deployment:

```dockerfile
# Dockerfile.api
FROM python:3.12
WORKDIR /app
COPY api/requirements.txt .
RUN pip install -r requirements.txt
COPY api/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -f Dockerfile.api -t claude-nine-api .
docker run -p 8000:8000 -v $(pwd)/api/claude_nine.db:/app/claude_nine.db claude-nine-api
```

---

## Next Steps

1. **Complete the Tutorial**: Follow the in-app guide when you visit http://localhost:3000
2. **Create Your First Team**: Teams → New Team (link to your git repository)
3. **Add Work Items**: Work Items → New Work Item (or import from Azure DevOps/Jira/GitHub)
4. **Start a Run**:
   - Select work items from the queue (up to max concurrent tasks)
   - Click "Start Run" - agents spawn automatically (1 per work item)
   - Monitor live telemetry in TaskCards
   - Watch the merge phase combine all work into an integration branch
5. **Create PR**: When complete, the integration branch is ready to push and create a PR

## Additional Resources

- **Bulk Assignment Guide**: [docs/bulk-assignment-guide.md](./bulk-assignment-guide.md)
- **API Documentation**: http://localhost:8000/docs (when running)
- **Interactive Tutorial**: Click `?` icon in dashboard header
- **GitHub Issues**: [github.com/bobum/Claude-Nine/issues](https://github.com/bobum/Claude-Nine/issues)

---

**Questions or Issues?**

1. Check troubleshooting section above
2. Review logs in terminal output
3. Visit the API docs: http://localhost:8000/docs
4. Open an issue on GitHub

**Enjoy your local AI development team!** 🚀
