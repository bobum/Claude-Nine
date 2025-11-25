# Claude-Nine Local Installation Script for Windows (PowerShell)
# This script sets up Claude-Nine to run entirely on your local machine

# Requires PowerShell 5.1 or later
#Requires -Version 5.1

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✓ $Message" "Green"
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "✗ $Message" "Red"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠ $Message" "Yellow"
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput $Message "Cyan"
}

# ASCII Art Banner
Write-ColorOutput @"

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

"@ "Blue"

Write-Success "Welcome to Claude-Nine!"
Write-Host "This installer will set up your AI development team platform locally."
Write-Host "No cloud services required (except Claude API for the AI)."
Write-Host ""

# Function to check if command exists
function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Check Prerequisites
Write-Info "[1/6] Checking Prerequisites..."
Write-Host ""

# Check Python
$pythonCmd = $null
if (Test-CommandExists "python") {
    $pythonVersion = python --version 2>&1 | Out-String
    if ($pythonVersion -match "Python (\d+\.\d+\.\d+)") {
        Write-Success "Python found: $pythonVersion"
        $pythonCmd = "python"
    }
}
elseif (Test-CommandExists "python3") {
    $pythonVersion = python3 --version 2>&1 | Out-String
    if ($pythonVersion -match "Python (\d+\.\d+\.\d+)") {
        Write-Success "Python 3 found: $pythonVersion"
        $pythonCmd = "python3"
    }
}

if (-not $pythonCmd) {
    Write-Error "Python 3.12+ is required but not found"
    Write-Host "  Please install Python from https://www.python.org/downloads/"
    exit 1
}

# Check pip
$pipCmd = $null
if (Test-CommandExists "pip") {
    Write-Success "pip found"
    $pipCmd = "pip"
}
elseif (Test-CommandExists "pip3") {
    Write-Success "pip3 found"
    $pipCmd = "pip3"
}
else {
    Write-Error "pip is required but not found"
    Write-Host "  Please install pip"
    exit 1
}

# Check Node.js
if (Test-CommandExists "node") {
    $nodeVersion = node --version
    Write-Success "Node.js found: $nodeVersion"
}
else {
    Write-Error "Node.js 18+ is required but not found"
    Write-Host "  Please install Node.js from https://nodejs.org/"
    exit 1
}

# Check npm
if (Test-CommandExists "npm") {
    $npmVersion = npm --version
    Write-Success "npm found: $npmVersion"
}
else {
    Write-Error "npm is required but not found"
    exit 1
}

# Check Git
if (Test-CommandExists "git") {
    $gitVersion = git --version
    Write-Success "Git found: $gitVersion"
}
else {
    Write-Warning "Git not found - optional but recommended for version control"
}

Write-Host ""
Write-Success "All prerequisites met!"
Write-Host ""

# Configure API Keys
Write-Info "[2/6] Configuring API Keys & Integrations..."
Write-Host ""
Write-Host "Claude-Nine uses Anthropic's Claude AI for intelligent agents."
Write-Host "You'll need an API key from: https://console.anthropic.com/settings/keys"
Write-Host ""

$keepExisting = $false
$anthropicApiKey = ""

# Check for existing API key
if (Test-Path "api\.env") {
    $envContent = Get-Content "api\.env" -Raw
    if ($envContent -match "ANTHROPIC_API_KEY") {
        Write-Success "Existing configuration found in api\.env"
        $useExisting = Read-Host "Do you want to keep the existing configuration? (y/n)"
        if ($useExisting -eq "y" -or $useExisting -eq "Y") {
            $keepExisting = $true
        }
    }
}

# Prompt for API keys if needed
$azureDevOpsUrl = ""
$azureDevOpsOrg = ""
$azureDevOpsToken = ""
$jiraUrl = ""
$jiraEmail = ""
$jiraApiToken = ""
$githubToken = ""
$linearApiKey = ""

if (-not $keepExisting) {
    $anthropicApiKey = Read-Host "Enter your Anthropic API key (or press Enter to set later)"
    if ([string]::IsNullOrWhiteSpace($anthropicApiKey)) {
        $anthropicApiKey = "your-api-key-here"
        Write-Warning "API key not set. You'll need to update api\.env before using Claude-Nine."
    }

    Write-Host ""
    Write-Info "Optional Integrations:"
    Write-Host "You can configure these now or later via the Settings page in the web UI."
    Write-Host ""

    # Azure DevOps
    Write-Info "Azure DevOps (press Enter to skip)"
    $azureDevOpsUrl = Read-Host "Azure DevOps URL (e.g., https://dev.azure.com)"
    if (-not [string]::IsNullOrWhiteSpace($azureDevOpsUrl)) {
        $azureDevOpsOrg = Read-Host "Organization name"
        $azureDevOpsToken = Read-Host "Personal Access Token"
    }
    Write-Host ""

    # Jira
    Write-Info "Jira (press Enter to skip)"
    $jiraUrl = Read-Host "Jira URL (e.g., https://yourcompany.atlassian.net)"
    if (-not [string]::IsNullOrWhiteSpace($jiraUrl)) {
        $jiraEmail = Read-Host "Jira email"
        $jiraApiToken = Read-Host "Jira API token"
    }
    Write-Host ""

    # GitHub
    Write-Info "GitHub (press Enter to skip)"
    $githubToken = Read-Host "GitHub Personal Access Token"
    Write-Host ""

    # Linear
    Write-Info "Linear (press Enter to skip)"
    $linearApiKey = Read-Host "Linear API key"
    Write-Host ""
}

# Set up API
Write-Info "[3/6] Setting Up API Server..."
Write-Host ""

Push-Location api

# Create .env file if not keeping existing
if (-not $keepExisting) {
    # Generate a secure secret key
    try {
        $secretKey = & $pythonCmd -c "import secrets; print(secrets.token_urlsafe(32))" 2>$null
        if ([string]::IsNullOrWhiteSpace($secretKey)) {
            throw "Python failed to generate key"
        }
    }
    catch {
        # Fallback to PowerShell random
        $secretKey = "change-me-$(Get-Random)-$(Get-Date -Format 'yyyyMMddHHmmss')"
    }

    Write-Host "Creating api\.env configuration..."

    $envContent = @"
# Claude-Nine API Configuration (Local Setup)

# Database - SQLite (no cloud database needed)
DATABASE_URL=sqlite:///./claude_nine.db

# Security
SECRET_KEY=$secretKey

# Anthropic API Key (required for Claude AI)
ANTHROPIC_API_KEY=$anthropicApiKey

# API Server Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Integration Credentials (Optional)
# You can also configure these via the Settings page in the web UI

# Azure DevOps
AZURE_DEVOPS_URL=$azureDevOpsUrl
AZURE_DEVOPS_ORGANIZATION=$azureDevOpsOrg
AZURE_DEVOPS_TOKEN=$azureDevOpsToken

# Jira
JIRA_URL=$jiraUrl
JIRA_EMAIL=$jiraEmail
JIRA_API_TOKEN=$jiraApiToken

# GitHub
GITHUB_TOKEN=$githubToken

# Linear
LINEAR_API_KEY=$linearApiKey
"@

    Set-Content -Path ".env" -Value $envContent
    Write-Success "Configuration file created: api\.env"
}

# Install Python dependencies
Write-Host ""
Write-Host "Upgrading pip to latest version..."
& $pythonCmd -m pip install --upgrade pip > $null 2>&1

Write-Host "Installing Python dependencies..."
$pipLog = "$env:TEMP\claude-nine-pip-install.log"
& $pipCmd install -r requirements.txt > $pipLog 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "Python dependencies installed"
}
else {
    Write-Warning "Some issues during pip install. Check $pipLog if problems occur."
    Write-Warning "If you see permission errors, try running PowerShell as Administrator."
}

Pop-Location

Write-Host ""

# Set up Dashboard
Write-Info "[4/6] Setting Up Dashboard..."
Write-Host ""

Push-Location dashboard

Write-Host "Installing Node.js dependencies (this may take a few minutes)..."
$npmLog = "$env:TEMP\claude-nine-npm-install.log"
npm install > $npmLog 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "Node.js dependencies installed"
}
else {
    Write-Error "npm install failed. Check $npmLog for details."
    exit 1
}

Pop-Location

Write-Host ""

# Create helper scripts
Write-Info "[5/6] Creating Helper Scripts..."
Write-Host ""

# Create start.ps1
$startScript = @"
# Start Claude-Nine (API + Dashboard)

Write-Host "Starting Claude-Nine..." -ForegroundColor Cyan
Write-Host ""

# Start API in background
Write-Host "Starting API server on http://localhost:8000..." -ForegroundColor Green
`$apiJob = Start-Job -ScriptBlock {
    Set-Location `$using:PWD\api
    $pythonCmd -m uvicorn app.main:app --host 0.0.0.0 --port 8000
}

# Wait for API to start
Start-Sleep -Seconds 3

# Start Dashboard in background
Write-Host "Starting Dashboard on http://localhost:3000..." -ForegroundColor Green
`$dashJob = Start-Job -ScriptBlock {
    Set-Location `$using:PWD\dashboard
    npm run dev
}

Write-Host ""
Write-Host "✓ Claude-Nine is starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard: http://localhost:3000"
Write-Host "  API: http://localhost:8000"
Write-Host "  API Docs: http://localhost:8000/docs"
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow
Write-Host ""

# Wait for jobs and handle Ctrl+C
try {
    Wait-Job `$apiJob, `$dashJob
}
finally {
    Write-Host "Stopping Claude-Nine..." -ForegroundColor Yellow
    Stop-Job `$apiJob, `$dashJob
    Remove-Job `$apiJob, `$dashJob

    # Kill any remaining processes
    Get-Process | Where-Object { `$_.Path -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id `$_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
"@

Set-Content -Path "start.ps1" -Value $startScript
Write-Success "Created start.ps1 - Run Claude-Nine with: .\start.ps1"

# Create stop.ps1
$stopScript = @'
# Stop Claude-Nine

Write-Host "Stopping Claude-Nine..." -ForegroundColor Yellow

# Kill API server
Get-Process | Where-Object { $_.Path -like "*uvicorn*" -or $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill processes on ports 8000 and 3000
Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}

Write-Host "✓ Claude-Nine stopped" -ForegroundColor Green
'@

Set-Content -Path "stop.ps1" -Value $stopScript
Write-Success "Created stop.ps1 - Stop Claude-Nine with: .\stop.ps1"

# Create api/run.ps1
$apiRunScript = @"
# Run the Claude-Nine API server

Set-Location `$PSScriptRoot

Write-Host "🚀 Starting Claude-Nine API..." -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 API will be available at:"
Write-Host "   - API: http://localhost:8000"
Write-Host "   - Docs: http://localhost:8000/docs"
Write-Host "   - Health: http://localhost:8000/health"
Write-Host ""

# Check if dependencies are installed
try {
    $pythonCmd -c "import fastapi" 2>`$null
    if (`$LASTEXITCODE -ne 0) {
        throw "FastAPI not found"
    }
}
catch {
    Write-Host "⚠️  Dependencies not installed. Installing..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host ""
}

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"@

Set-Content -Path "api\run.ps1" -Value $apiRunScript
Write-Success "Created api\run.ps1"

Write-Host ""

# Create GETTING_STARTED.md
Write-Info "[6/6] Finalizing Installation..."
Write-Host ""

$gettingStarted = @'
# Getting Started with Claude-Nine (Windows)

## Quick Start

### Start Claude-Nine

**Using PowerShell (Recommended):**
```powershell
.\start.ps1
```

**Using Batch:**
```batch
start.bat
```

Or double-click `start.bat` in Windows Explorer.

This starts both the API server and dashboard. Open http://localhost:3000 in your browser.

### Stop Claude-Nine

**Using PowerShell:**
```powershell
.\stop.ps1
```

**Using Batch:**
```batch
stop.bat
```

Or close the terminal windows.

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
Your Anthropic API key is stored in `api\.env`. To update it:
- Open `api\.env` in Notepad or your favorite editor
- Edit the ANTHROPIC_API_KEY line

### Database
Your data is stored in `api\claude_nine.db` (SQLite file).
- No cloud database needed
- Portable - just copy the file to backup

## Troubleshooting

### PowerShell Execution Policy
If you get an error running .ps1 scripts:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port Already in Use
If port 8000 or 3000 is already taken:
```powershell
.\stop.ps1
```

Or manually:
```powershell
Get-NetTCPConnection -LocalPort 8000,3000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### API Not Starting
Check if your Anthropic API key is set in `api\.env`.

### Dashboard Build Errors
Try clearing node_modules:
```batch
cd dashboard
rmdir /s /q node_modules
del package-lock.json
npm install
cd ..
```

## Documentation

- **Full Guide**: See `docs\local-setup-guide.md`
- **Bulk Assignment**: See `docs\bulk-assignment-guide.md`
- **API Reference**: http://localhost:8000/docs (when API is running)

## Where Everything Lives

```
Claude-Nine\
├── api\                    # Backend (FastAPI)
│   ├── claude_nine.db      # Your local database
│   ├── .env                # Configuration (API keys)
│   └── app\                # API code
├── dashboard\              # Frontend (Next.js)
│   └── app\                # Dashboard pages
├── start.ps1               # Start Claude-Nine (PowerShell)
├── start.bat               # Start Claude-Nine (Batch)
├── stop.ps1                # Stop Claude-Nine (PowerShell)
├── stop.bat                # Stop Claude-Nine (Batch)
└── GETTING_STARTED_WINDOWS.md  # This file
```

## Need Help?

- Check the tutorial (? icon in dashboard header)
- Read the docs in `docs\`
- View API documentation at http://localhost:8000/docs
- Check issues at https://github.com/bobum/Claude-Nine/issues

---

**Happy coding with your AI development team! 🚀**
'@

Set-Content -Path "GETTING_STARTED_WINDOWS.md" -Value $gettingStarted
Write-Success "Created GETTING_STARTED_WINDOWS.md"

Write-Host ""
Write-ColorOutput "═══════════════════════════════════════════════════════════" "Green"
Write-ColorOutput "                                                           " "Green"
Write-ColorOutput "  ✓ Installation Complete!                                " "Green"
Write-ColorOutput "                                                           " "Green"
Write-ColorOutput "═══════════════════════════════════════════════════════════" "Green"
Write-Host ""

Write-Info "Next Steps:"
Write-Host ""
Write-Host "1. Start Claude-Nine:"
Write-ColorOutput "   .\start.ps1" "Yellow"
Write-Host ""
Write-Host "2. Open your browser to:"
Write-ColorOutput "   http://localhost:3000" "Yellow"
Write-Host ""
Write-Host "3. Follow the interactive tutorial to get started!"
Write-Host ""

Write-Info "Additional Information:"
Write-Host ""
Write-Host "  📖 Quick Guide: GETTING_STARTED_WINDOWS.md"
Write-Host "  🛑 Stop Server: .\stop.ps1"
Write-Host "  📚 Full Docs: docs\"
Write-Host "  🔧 API Docs: http://localhost:8000/docs (when running)"
Write-Host ""

if ($anthropicApiKey -eq "your-api-key-here") {
    Write-Warning "IMPORTANT: Update your API key in api\.env before starting!"
    Write-Host ""
}

Write-Success "Enjoy your AI development team! 🤖"
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
