#!/bin/bash

# Claude-Nine Local Installation Script
# This script sets up Claude-Nine to run entirely on your local machine

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ASCII Art Banner
echo -e "${BLUE}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║  ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗      █████╗       ║
║ ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝     ██╔══██╗      ║
║ ██║     ██║     ███████║██║   ██║██║  ██║█████╗ █████╗╚██████║      ║
║ ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝ ╚════╝ ╚═══██║      ║
║ ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗     █████╔╝       ║
║  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝     ╚════╝        ║
║                                                                       ║
║                    Local Installation Wizard                          ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${GREEN}Welcome to Claude-Nine!${NC}"
echo "This installer will set up your AI development team platform locally."
echo "No cloud services required (except Claude API for the AI)."
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get version
get_version() {
    local cmd=$1
    local version_flag=${2:---version}
    $cmd $version_flag 2>&1 | head -n1
}

echo -e "${BLUE}[1/6] Checking Prerequisites...${NC}"
echo ""

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python 3 found: $PYTHON_VERSION"
    PYTHON_CMD=python3
elif command_exists python; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python found: $PYTHON_VERSION"
    PYTHON_CMD=python
else
    echo -e "${RED}✗ Python 3.12+ is required but not found${NC}"
    echo "  Please install Python from https://www.python.org/downloads/"
    exit 1
fi

# Check pip
if command_exists pip3; then
    echo -e "${GREEN}✓${NC} pip3 found"
    PIP_CMD=pip3
elif command_exists pip; then
    echo -e "${GREEN}✓${NC} pip found"
    PIP_CMD=pip
else
    echo -e "${RED}✗ pip is required but not found${NC}"
    echo "  Please install pip"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Node.js found: $NODE_VERSION"
else
    echo -e "${RED}✗ Node.js 18+ is required but not found${NC}"
    echo "  Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓${NC} npm found: $NPM_VERSION"
else
    echo -e "${RED}✗ npm is required but not found${NC}"
    exit 1
fi

# Check Git
if command_exists git; then
    GIT_VERSION=$(git --version)
    echo -e "${GREEN}✓${NC} Git found: $GIT_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Git not found - optional but recommended for version control"
fi

echo ""
echo -e "${GREEN}All prerequisites met!${NC}"
echo ""

# Get Anthropic API Key
echo -e "${BLUE}[2/6] Configuring API Key...${NC}"
echo ""
echo "Claude-Nine uses Anthropic's Claude AI for intelligent agents."
echo "You'll need an API key from: https://console.anthropic.com/settings/keys"
echo ""

# Check if API key already exists
if [ -f "api/.env" ] && grep -q "ANTHROPIC_API_KEY" api/.env 2>/dev/null; then
    EXISTING_KEY=$(grep "ANTHROPIC_API_KEY" api/.env | cut -d '=' -f2)
    if [ ! -z "$EXISTING_KEY" ] && [ "$EXISTING_KEY" != "your-api-key-here" ]; then
        echo -e "${GREEN}✓${NC} Existing API key found in api/.env"
        read -p "Do you want to use the existing key? (y/n): " USE_EXISTING
        if [[ $USE_EXISTING =~ ^[Yy]$ ]]; then
            ANTHROPIC_API_KEY=$EXISTING_KEY
        fi
    fi
fi

# Prompt for API key if not set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    read -p "Enter your Anthropic API key (or press Enter to set it later): " ANTHROPIC_API_KEY
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        ANTHROPIC_API_KEY="your-api-key-here"
        echo -e "${YELLOW}⚠${NC} API key not set. You'll need to update api/.env before using Claude-Nine."
    fi
fi

echo ""

# Set up API
echo -e "${BLUE}[3/6] Setting Up API Server...${NC}"
echo ""

cd api

# Create .env file
echo "Creating api/.env configuration..."
cat > .env << EOF
# Claude-Nine API Configuration (Local Setup)

# Database - SQLite (no cloud database needed)
DATABASE_URL=sqlite:///./claude_nine.db

# Anthropic API Key (required for Claude AI)
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# API Server Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
EOF

echo -e "${GREEN}✓${NC} Configuration file created: api/.env"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
if $PIP_CMD install -r requirements.txt > /tmp/claude-nine-pip-install.log 2>&1; then
    echo -e "${GREEN}✓${NC} Python dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} Some issues during pip install. Check /tmp/claude-nine-pip-install.log if problems occur."
fi

cd ..

echo ""

# Set up Dashboard
echo -e "${BLUE}[4/6] Setting Up Dashboard...${NC}"
echo ""

cd dashboard

echo "Installing Node.js dependencies (this may take a few minutes)..."
if npm install > /tmp/claude-nine-npm-install.log 2>&1; then
    echo -e "${GREEN}✓${NC} Node.js dependencies installed"
else
    echo -e "${RED}✗${NC} npm install failed. Check /tmp/claude-nine-npm-install.log for details."
    exit 1
fi

cd ..

echo ""

# Create helper scripts
echo -e "${BLUE}[5/6] Creating Helper Scripts...${NC}"
echo ""

# Create start script
cat > start.sh << 'EOF'
#!/bin/bash

# Start Claude-Nine (API + Dashboard)

echo "Starting Claude-Nine..."
echo ""

# Start API in background
echo "Starting API server on http://localhost:8000..."
cd api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
cd ..

# Wait for API to start
sleep 3

# Start Dashboard in background
echo "Starting Dashboard on http://localhost:3000..."
cd dashboard
npm run dev &
DASHBOARD_PID=$!
cd ..

echo ""
echo "✓ Claude-Nine is starting up!"
echo ""
echo "  Dashboard: http://localhost:3000"
echo "  API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "echo 'Stopping Claude-Nine...'; kill $API_PID $DASHBOARD_PID 2>/dev/null; exit" SIGINT SIGTERM

wait
EOF

chmod +x start.sh
echo -e "${GREEN}✓${NC} Created start.sh - Run Claude-Nine with: ./start.sh"

# Create stop script
cat > stop.sh << 'EOF'
#!/bin/bash

# Stop Claude-Nine

echo "Stopping Claude-Nine..."

# Kill API server
pkill -f "uvicorn app.main:app" 2>/dev/null

# Kill Dashboard
pkill -f "next dev" 2>/dev/null
pkill -f "node.*next" 2>/dev/null

echo "✓ Claude-Nine stopped"
EOF

chmod +x stop.sh
echo -e "${GREEN}✓${NC} Created stop.sh - Stop Claude-Nine with: ./stop.sh"

echo ""

# Create README for user
echo -e "${BLUE}[6/6] Finalizing Installation...${NC}"
echo ""

cat > GETTING_STARTED.md << 'EOF'
# Getting Started with Claude-Nine

## Quick Start

### Start Claude-Nine
```bash
./start.sh
```

This starts both the API server and dashboard. Open http://localhost:3000 in your browser.

### Stop Claude-Nine
```bash
./stop.sh
```

Or press `Ctrl+C` in the terminal where you ran `./start.sh`.

## What's Running?

- **Dashboard**: http://localhost:3000 - Your main UI
- **API**: http://localhost:8000 - Backend server
- **API Docs**: http://localhost:8000/docs - Interactive API documentation

## First Steps

1. **Visit the Dashboard**: http://localhost:3000
2. **Follow the Tutorial**: An interactive tour will guide you through features
3. **Create Your First Team**:
   - Click "View Teams" → "+ New Team"
   - Add agents to your team
4. **Add Work Items**:
   - Click "View Work Items" → "+ New Work Item"
   - Or integrate with Azure DevOps/Jira/GitHub
5. **Assign Work & Start**:
   - Use bulk assignment to queue work for your team
   - Start the team and watch your AI agents work!

## Configuration

### API Key
Your Anthropic API key is stored in `api/.env`. To update it:
```bash
nano api/.env  # or use your favorite editor
# Edit the ANTHROPIC_API_KEY line
```

### Database
Your data is stored in `api/claude_nine.db` (SQLite file).
- No cloud database needed
- Portable - just copy the file to backup
- View with: `sqlite3 api/claude_nine.db`

## Troubleshooting

### Port Already in Use
If port 8000 or 3000 is already taken:
```bash
# Kill existing process
./stop.sh

# Or manually:
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### API Not Starting
Check if your Anthropic API key is set in `api/.env`.

### Dashboard Build Errors
Try clearing node_modules:
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
cd ..
```

## Documentation

- **Full Guide**: See `docs/local-setup-guide.md`
- **Bulk Assignment**: See `docs/bulk-assignment-guide.md`
- **API Reference**: http://localhost:8000/docs (when API is running)

## Where Everything Lives

```
Claude-Nine/
├── api/                    # Backend (FastAPI)
│   ├── claude_nine.db      # Your local database
│   ├── .env                # Configuration (API keys)
│   └── app/                # API code
├── dashboard/              # Frontend (Next.js)
│   └── app/                # Dashboard pages
├── start.sh                # Start Claude-Nine
├── stop.sh                 # Stop Claude-Nine
└── GETTING_STARTED.md      # This file
```

## Need Help?

- Check the tutorial (? icon in dashboard header)
- Read the docs in `docs/`
- View API documentation at http://localhost:8000/docs
- Check issues at https://github.com/bobum/Claude-Nine/issues

---

**Happy coding with your AI development team! 🚀**
EOF

echo -e "${GREEN}✓${NC} Created GETTING_STARTED.md"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  ✓ Installation Complete!                                  ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Start Claude-Nine:"
echo -e "   ${YELLOW}./start.sh${NC}"
echo ""
echo "2. Open your browser to:"
echo -e "   ${YELLOW}http://localhost:3000${NC}"
echo ""
echo "3. Follow the interactive tutorial to get started!"
echo ""
echo -e "${BLUE}Additional Information:${NC}"
echo ""
echo "  📖 Quick Guide: GETTING_STARTED.md"
echo "  🛑 Stop Server: ./stop.sh"
echo "  📚 Full Docs: docs/"
echo "  🔧 API Docs: http://localhost:8000/docs (when running)"
echo ""

if [ "$ANTHROPIC_API_KEY" == "your-api-key-here" ]; then
    echo -e "${YELLOW}⚠ IMPORTANT: Update your API key in api/.env before starting!${NC}"
    echo ""
fi

echo -e "${GREEN}Enjoy your AI development team! 🤖${NC}"
echo ""
