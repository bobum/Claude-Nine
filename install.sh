#!/bin/bash

# Claude-Nine Local Installation Script
# This script sets up Claude-Nine to run entirely on your local machine
# Now with Python 3.13 virtual environment support

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

# Spinner function that shows progress from a log file
# Usage: spin_with_progress <pid> <log_file> <message>
spin_with_progress() {
    local pid=$1
    local log_file=$2
    local message=$3
    local spin_chars='|/-\'
    local i=0
    local last_pkg=""
    local line_width=70

    # Hide cursor
    tput civis 2>/dev/null || true

    while kill -0 $pid 2>/dev/null; do
        # Get current package being installed from log
        if [ -f "$log_file" ]; then
            # Look for pip style "Collecting package" or npm style output
            local current=$(grep -oE "Collecting [a-zA-Z0-9_-]+" "$log_file" 2>/dev/null | tail -1)
            if [ -z "$current" ]; then
                current=$(grep -oE "Downloading [a-zA-Z0-9_-]+" "$log_file" 2>/dev/null | tail -1)
            fi
            if [ -n "$current" ] && [ "$current" != "$last_pkg" ]; then
                last_pkg="$current"
            fi
        fi

        local char="${spin_chars:$i:1}"
        i=$(( (i + 1) % 4 ))

        # Build the status line
        local status_line
        if [ -n "$last_pkg" ]; then
            status_line="[${char}] ${message}: ${last_pkg}"
        else
            status_line="[${char}] ${message}..."
        fi

        # Pad to fixed width to overwrite previous content
        printf "\r%-${line_width}s" "$status_line"

        sleep 0.15
    done

    # Show cursor again
    tput cnorm 2>/dev/null || true

    # Clear the line with spaces
    printf "\r%-${line_width}s\r" " "
}

echo -e "${BLUE}[1/7] Checking Prerequisites...${NC}"
echo ""

# Check for Python 3.13 specifically (required for CrewAI)
PYTHON_CMD=""
PYTHON_VERSION=""

# Try py -3.13 first (Windows Python Launcher)
if command_exists py && py -3.13 --version >/dev/null 2>&1; then
    PYTHON_VERSION=$(py -3.13 --version 2>&1 | awk '{print $2}')
    PYTHON_CMD="py -3.13"
    echo -e "${GREEN}✓${NC} Python 3.13 found via py launcher: $PYTHON_VERSION"
# Try python3.13
elif python3.13 --version >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3.13 --version 2>&1 | awk '{print $2}')
    PYTHON_CMD=python3.13
    echo -e "${GREEN}✓${NC} Python 3.13 found: $PYTHON_VERSION"
# Check if default python is 3.13
elif python --version 2>&1 | grep -q "3.13"; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    PYTHON_CMD=python
    echo -e "${GREEN}✓${NC} Python 3.13 found: $PYTHON_VERSION"
elif python3 --version 2>&1 | grep -q "3.13"; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_CMD=python3
    echo -e "${GREEN}✓${NC} Python 3.13 found: $PYTHON_VERSION"
else
    echo -e "${RED}✗ Python 3.13 is required but not found${NC}"
    echo ""
    echo "  CrewAI (used by the orchestrator) requires Python 3.10-3.13"
    echo "  Python 3.14 is too new and not yet supported."
    echo ""
    echo "  Please install Python 3.13 from:"
    echo "  https://www.python.org/downloads/release/python-3130/"
    echo ""
    echo "  You can install it alongside your current Python version."
    echo ""
    exit 1
fi

# Check for Python 3.14+ and warn (causes venv conflicts)
PYTHON_314_FOUND=false
if command_exists py && py -3.14 --version >/dev/null 2>&1; then
    PYTHON_314_FOUND=true
    PYTHON_314_VERSION=$(py -3.14 --version 2>&1 | awk '{print $2}')
elif python3.14 --version >/dev/null 2>&1; then
    PYTHON_314_FOUND=true
    PYTHON_314_VERSION=$(python3.14 --version 2>&1 | awk '{print $2}')
elif python --version 2>&1 | grep -q "3.14"; then
    PYTHON_314_FOUND=true
    PYTHON_314_VERSION=$(python --version 2>&1 | awk '{print $2}')
elif python3 --version 2>&1 | grep -q "3.14"; then
    PYTHON_314_FOUND=true
    PYTHON_314_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
fi

if [ "$PYTHON_314_FOUND" = true ]; then
    echo ""
    echo -e "${RED}✗ WARNING: Python 3.14+ detected ($PYTHON_314_VERSION)${NC}"
    echo ""
    echo "  Python 3.14 is NOT compatible with Claude-Nine because:"
    echo "  - CrewAI requires Python 3.10-3.13"
    echo "  - Having Python 3.14 installed causes virtual environment conflicts"
    echo "  - The venv may leak and use Python 3.14's packages incorrectly"
    echo ""
    echo "  Please uninstall Python 3.14 before continuing."
    echo "  You can keep Python 3.13 as your only Python installation."
    echo ""
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

# Check GitHub CLI (required for automatic PR creation)
if command_exists gh; then
    GH_VERSION=$(gh --version | head -1)
    echo -e "${GREEN}✓${NC} GitHub CLI found: $GH_VERSION"

    # Check if gh is authenticated
    if gh auth status >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} GitHub CLI is authenticated"
    else
        echo -e "${YELLOW}⚠${NC} GitHub CLI is not authenticated"
        echo "  Run 'gh auth login' to authenticate for automatic PR creation"
    fi
else
    echo -e "${RED}✗ GitHub CLI (gh) is required but not found${NC}"
    echo ""
    echo "  The orchestrator uses 'gh' to automatically create pull requests"
    echo "  after merging feature branches."
    echo ""
    echo "  Install from: https://cli.github.com/"
    echo ""
    echo "  After installing, run: gh auth login"
    echo ""
    exit 1
fi

echo ""

# Check Redis/Docker availability (for Celery task queue)
REDIS_METHOD=""
echo ""
echo -e "${BLUE}Checking Redis availability (for task queue)...${NC}"

# Check if Redis is already running
if command_exists redis-cli && redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is already running on localhost"
    REDIS_METHOD="system"
# Check if Docker is available
elif command_exists docker; then
    # Check if Docker daemon is running
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker found - will use containerized Redis"
        REDIS_METHOD="docker"

        # Pull Redis image
        echo "  Pulling Redis image..."
        docker pull redis:alpine -q >/dev/null 2>&1 || docker pull redis:alpine
        echo -e "${GREEN}  ✓${NC} Redis image ready"
    else
        echo -e "${YELLOW}⚠${NC} Docker found but daemon not running"
    fi
fi

if [ -z "$REDIS_METHOD" ]; then
    echo -e "${YELLOW}⚠${NC} No Redis detected"
    echo ""
    echo "  Claude-Nine uses Redis for the task queue (Celery)."
    echo "  Please do ONE of the following:"
    echo ""
    echo "  Option 1: Install Docker (recommended)"
    echo "    https://docs.docker.com/get-docker/"
    echo ""
    echo "  Option 2: Install Redis directly"
    echo "    - Windows: Use WSL2 or Docker"
    echo "    - macOS: brew install redis"
    echo "    - Linux: sudo apt install redis-server"
    echo ""
    echo -e "  ${YELLOW}Installation will continue, but start.sh will need Redis.${NC}"
fi

echo -e "${GREEN}All prerequisites met!${NC}"
echo ""

# Function to remove venv directory robustly on Windows
remove_venv() {
    local venv_dir="$1"
    echo "Removing existing virtual environment..."

    # On Windows/Git Bash, use a more robust removal strategy
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
        # First, try to kill any Python processes that might be using the venv
        echo "Checking for running Python processes..."
        taskkill //F //IM python.exe 2>/dev/null || true
        sleep 1

        # Try multiple removal methods with timeout
        echo "Attempting to remove venv directory..."

        # Method 1: Standard rm with timeout (30 seconds)
        timeout 30 rm -rf "$venv_dir" 2>/dev/null && echo "Removed with rm -rf" && return 0

        # Method 2: Remove files first, then directories
        echo "Trying alternative removal method..."
        find "$venv_dir" -type f -delete 2>/dev/null || true
        find "$venv_dir" -type d -delete 2>/dev/null || true

        # Method 3: Use PowerShell if available (more reliable on Windows)
        if command -v powershell.exe >/dev/null 2>&1; then
            echo "Using PowerShell for removal..."
            powershell.exe -Command "Remove-Item -Path '$venv_dir' -Recurse -Force -ErrorAction SilentlyContinue" 2>/dev/null || true
        fi

        # Verify removal
        if [ -d "$venv_dir" ]; then
            echo -e "${YELLOW}Warning: Could not fully remove venv directory.${NC}"
            echo "Please manually delete the 'venv' folder and run install.sh again."
            echo "Or press Ctrl+C to cancel and manually delete it."
            read -p "Press Enter to continue anyway (not recommended)..." dummy
        else
            echo -e "${GREEN}✓${NC} Virtual environment removed successfully"
        fi
    else
        # Unix/Linux/Mac: standard removal
        rm -rf "$venv_dir"
        echo -e "${GREEN}✓${NC} Virtual environment removed"
    fi
}

# Create virtual environment
echo -e "${BLUE}[2/7] Creating Python Virtual Environment...${NC}"
echo ""

VENV_DIR="venv"

# Always remove existing venv and create fresh one for clean install
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Existing virtual environment found${NC}"
    remove_venv "$VENV_DIR"
fi

echo "Creating virtual environment with Python 3.13..."
$PYTHON_CMD -m venv "$VENV_DIR"
echo -e "${GREEN}✓${NC} Virtual environment created at $VENV_DIR"

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Git Bash on Windows
    source "$VENV_DIR/Scripts/activate"
else
    # Linux/Mac
    source "$VENV_DIR/bin/activate"
fi

# Verify we're using the venv Python
VENV_PYTHON=$(which python)
echo -e "${GREEN}✓${NC} Using Python from: $VENV_PYTHON"

echo ""

# Get API Keys and Integration Credentials
echo -e "${BLUE}[3/7] Configuring API Keys & Integrations...${NC}"
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

# Prompt for Anthropic API key if not set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    read -p "Enter your Anthropic API key (or press Enter to set it later): " ANTHROPIC_API_KEY
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        ANTHROPIC_API_KEY="your-api-key-here"
        echo -e "${YELLOW}⚠${NC} API key not set. You'll need to update api/.env before using Claude-Nine."
    fi
fi

echo ""
echo -e "${BLUE}Optional Integrations:${NC}"
echo "You can configure these now or later via the Settings page in the web UI."
echo ""

# Azure DevOps
echo -e "${BLUE}Azure DevOps${NC} (press Enter to skip)"
read -p "Azure DevOps URL (e.g., https://dev.azure.com): " AZURE_DEVOPS_URL
if [ ! -z "$AZURE_DEVOPS_URL" ]; then
    read -p "Organization name: " AZURE_DEVOPS_ORGANIZATION
    read -p "Personal Access Token: " AZURE_DEVOPS_TOKEN
fi
echo ""

# Jira
echo -e "${BLUE}Jira${NC} (press Enter to skip)"
read -p "Jira URL (e.g., https://yourcompany.atlassian.net): " JIRA_URL
if [ ! -z "$JIRA_URL" ]; then
    read -p "Jira email: " JIRA_EMAIL
    read -p "Jira API token: " JIRA_API_TOKEN
fi
echo ""

# GitHub
echo -e "${BLUE}GitHub${NC} (press Enter to skip)"
read -p "GitHub Personal Access Token: " GITHUB_TOKEN
echo ""

# Linear
echo -e "${BLUE}Linear${NC} (press Enter to skip)"
read -p "Linear API key: " LINEAR_API_KEY
echo ""

# Set up API
echo -e "${BLUE}[4/7] Setting Up API Server...${NC}"
echo ""

cd api

# Generate a secure secret key
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32 2>/dev/null || echo "change-me-$(date +%s)-$(shuf -i 1000-9999 -n 1)")

# Create .env file
echo "Creating api/.env configuration..."
cat > .env << EOF
# Claude-Nine API Configuration (Local Setup)

# Database - SQLite (no cloud database needed)
DATABASE_URL=sqlite:///./claude_nine.db

# Security
SECRET_KEY=$SECRET_KEY

# Anthropic API Key (required for Claude AI)
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# API Server Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Celery / Redis Task Queue
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Integration Credentials (Optional)
# You can also configure these via the Settings page in the web UI

# Azure DevOps
AZURE_DEVOPS_URL=$AZURE_DEVOPS_URL
AZURE_DEVOPS_ORGANIZATION=$AZURE_DEVOPS_ORGANIZATION
AZURE_DEVOPS_TOKEN=$AZURE_DEVOPS_TOKEN

# Jira
JIRA_URL=$JIRA_URL
JIRA_EMAIL=$JIRA_EMAIL
JIRA_API_TOKEN=$JIRA_API_TOKEN

# GitHub
GITHUB_TOKEN=$GITHUB_TOKEN

# Linear
LINEAR_API_KEY=$LINEAR_API_KEY
EOF

echo -e "${GREEN}✓${NC} Configuration file created: api/.env"

# Install Python dependencies for API
echo ""
echo "Upgrading pip to latest version..."
python -m pip install --upgrade pip --quiet

echo "Installing API dependencies..."
API_LOG="/tmp/claude-nine-api-deps.log"
pip install -r requirements.txt > "$API_LOG" 2>&1 &
PIP_PID=$!
spin_with_progress $PIP_PID "$API_LOG" "Installing API packages"
wait $PIP_PID
PIP_EXIT=$?
if [ $PIP_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} API dependencies installed"
else
    echo -e "${RED}✗${NC} Failed to install API dependencies"
    echo "See $API_LOG for details"
    exit 1
fi

cd ..

echo ""

# Install orchestrator dependencies
echo -e "${BLUE}[5/7] Setting Up Orchestrator...${NC}"
echo ""

cd claude-multi-agent-orchestrator

echo "Installing orchestrator dependencies (CrewAI has many packages)..."
ORCH_LOG="/tmp/claude-nine-orch-deps.log"
pip install -r requirements.txt > "$ORCH_LOG" 2>&1 &
PIP_PID=$!
spin_with_progress $PIP_PID "$ORCH_LOG" "Installing orchestrator packages"
wait $PIP_PID
PIP_EXIT=$?
if [ $PIP_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Orchestrator dependencies installed"
else
    echo -e "${RED}✗${NC} Failed to install orchestrator dependencies"
    echo "This may be due to Python version compatibility."
    echo "Please ensure you're using Python 3.10-3.13"
    echo "See $ORCH_LOG for details"
    exit 1
fi

cd ..

echo ""

# Set up Dashboard
echo -e "${BLUE}[6/7] Setting Up Dashboard...${NC}"
echo ""

cd dashboard

echo "Installing Node.js dependencies..."
NPM_LOG="/tmp/claude-nine-npm-install.log"
npm install > "$NPM_LOG" 2>&1 &
NPM_PID=$!
spin_with_progress $NPM_PID "$NPM_LOG" "Installing npm packages"
wait $NPM_PID
NPM_EXIT=$?
if [ $NPM_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Node.js dependencies installed"
else
    echo -e "${RED}✗${NC} npm install failed. See $NPM_LOG for details."
    exit 1
fi

echo "Building dashboard..."
BUILD_LOG="/tmp/claude-nine-npm-build.log"
npm run build > "$BUILD_LOG" 2>&1 &
BUILD_PID=$!
spin_with_progress $BUILD_PID "$BUILD_LOG" "Building dashboard"
wait $BUILD_PID
BUILD_EXIT=$?
if [ $BUILD_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Dashboard built successfully"
else
    echo -e "${RED}✗${NC} Dashboard build failed. See $BUILD_LOG for details."
    echo "You can still try running with: npm run dev (development mode)"
    # Don't exit - dev mode might still work
fi

cd ..

echo ""

# Create helper scripts
echo -e "${BLUE}[7/7] Creating Helper Scripts...${NC}"
echo ""

# Determine activation command based on OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    ACTIVATE_CMD="source venv/Scripts/activate"
else
    ACTIVATE_CMD="source venv/bin/activate"
fi


# Scripts are already in the repo with Redis + Celery support
chmod +x start.sh stop.sh 2>/dev/null || true
echo -e "${GREEN}✓${NC} start.sh ready - Run Claude-Nine with: ./start.sh"
echo -e "${GREEN}✓${NC} stop.sh ready - Stop Claude-Nine with: ./stop.sh"

cat > activate.sh << EOF
#!/bin/bash

# Activate the Claude-Nine Python virtual environment

echo "Activating Claude-Nine virtual environment..."
$ACTIVATE_CMD

echo ""
echo -e "\033[0;32m✓ Virtual environment activated\033[0m"
echo ""
echo "You can now run Python commands using the venv Python 3.13:"
echo "  python --version"
echo "  pip list"
echo ""
echo "To deactivate, type: deactivate"
echo ""
EOF

chmod +x activate.sh
echo -e "${GREEN}✓${NC} Created activate.sh - Activate venv with: source activate.sh"
# Create or update .gitignore for logs and venv
if ! grep -q "^logs/$" .gitignore 2>/dev/null; then
    echo "logs/" >> .gitignore
fi
if ! grep -q "^venv/$" .gitignore 2>/dev/null; then
    echo "venv/" >> .gitignore
fi
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
echo -e "   ${YELLOW}http://localhost:3001${NC}"
echo ""
echo "3. Follow the interactive tutorial to get started!"
echo ""
echo -e "${BLUE}Additional Information:${NC}"
echo ""
echo "  📖 Quick Guide: GETTING_STARTED.md"
echo "  🛑 Stop Server: ./stop.sh"
echo "  🐍 Activate venv: source activate.sh"
echo "  📚 Full Docs: docs/"
echo "  🔧 API Docs: http://localhost:8000/docs (when running)"
echo ""

if [ "$ANTHROPIC_API_KEY" == "your-api-key-here" ]; then
    echo -e "${YELLOW}⚠ IMPORTANT: Update your API key in api/.env before starting!${NC}"
    echo ""
fi

echo -e "${GREEN}Enjoy your AI development team! 🤖${NC}"
echo ""
