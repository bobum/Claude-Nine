# Verify Prerequisites

Check all system requirements before running Claude-Nine.

## Quick Check Script

Run these commands to verify your environment:

```bash
echo "=== Python ==="
python --version
# Required: 3.12+

echo ""
echo "=== Node.js ==="
node --version
# Required: 18+

echo ""
echo "=== npm ==="
npm --version
# Required: 8+

echo ""
echo "=== Git ==="
git --version
# Required: 2.7+ (for worktree support)

echo ""
echo "=== Virtual Environment ==="
ls -la venv/
# Should exist in project root

echo ""
echo "=== API Key ==="
if [ -n "$ANTHROPIC_API_KEY" ]; then
  echo "ANTHROPIC_API_KEY is set (${ANTHROPIC_API_KEY:0:12}...)"
else
  echo "WARNING: ANTHROPIC_API_KEY is NOT set"
fi

echo ""
echo "=== Database ==="
ls -la api/claude_nine.db
# Should exist after first run

echo ""
echo "=== Ports ==="
lsof -i :8000 2>/dev/null || echo "Port 8000: Available"
lsof -i :3001 2>/dev/null || echo "Port 3001: Available"
```

## Detailed Requirements

### Python 3.12+

```bash
python --version
# Python 3.12.x or higher

# If not installed:
# Windows: Download from python.org
# Mac: brew install python@3.12
# Linux: sudo apt install python3.12
```

### Node.js 18+

```bash
node --version
# v18.x.x or higher

# If not installed:
# Use nvm: nvm install 18
# Or download from nodejs.org
```

### Git 2.7+

```bash
git --version
# git version 2.7.x or higher (for worktree support)

# Update if needed:
# Mac: brew upgrade git
# Linux: sudo apt upgrade git
```

### Virtual Environment

```bash
# Check if exists
ls venv/

# Create if missing
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# OR
. venv/Scripts/activate   # Windows

# Install dependencies
pip install -r api/requirements.txt
pip install -r claude-multi-agent-orchestrator/requirements.txt
```

### Anthropic API Key

```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Set in environment
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Or add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> api/.env
```

### Dashboard Dependencies

```bash
cd dashboard

# Check package.json exists
ls package.json

# Install if missing
npm install

# Verify build works
npm run build
```

## Troubleshooting

### Python version too old

```bash
# Install pyenv for version management
curl https://pyenv.run | bash

# Install Python 3.12
pyenv install 3.12
pyenv global 3.12
```

### Node version too old

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install Node 18
nvm install 18
nvm use 18
```

### Git worktree not supported

```bash
# Check git version
git --version

# If < 2.7, upgrade git
# Mac: brew upgrade git
# Linux: sudo add-apt-repository ppa:git-core/ppa && sudo apt update && sudo apt install git
```

### API key invalid

```bash
# Test key works
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# Should return a response, not an error
```

## Status Checklist

| Requirement | Command | Expected |
|-------------|---------|----------|
| Python | `python --version` | 3.12+ |
| Node.js | `node --version` | 18+ |
| npm | `npm --version` | 8+ |
| Git | `git --version` | 2.7+ |
| venv | `ls venv/` | Directory exists |
| API Key | `echo $ANTHROPIC_API_KEY` | sk-ant-... |
| Database | `ls api/claude_nine.db` | File exists |
| Port 8000 | `lsof -i :8000` | Available or API running |
| Port 3001 | `lsof -i :3001` | Available or Dashboard running |
