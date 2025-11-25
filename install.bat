@echo off
REM Claude-Nine Local Installation Script for Windows
REM This script sets up Claude-Nine to run entirely on your local machine

setlocal enabledelayedexpansion

REM Colors are limited in batch, but we can use echo for clarity

REM ASCII Art Banner
echo.
echo ========================================================================
echo.
echo   ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗      █████╗
echo  ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝     ██╔══██╗
echo  ██║     ██║     ███████║██║   ██║██║  ██║█████╗ █████╗╚██████║
echo  ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝ ╚════╝ ╚═══██║
echo  ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗     █████╔╝
echo   ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝     ╚════╝
echo.
echo                     Local Installation Wizard
echo.
echo ========================================================================
echo.

echo Welcome to Claude-Nine!
echo This installer will set up your AI development team platform locally.
echo No cloud services required (except Claude API for the AI).
echo.

REM Check Prerequisites
echo [1/6] Checking Prerequisites...
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] !PYTHON_VERSION!
    set PYTHON_CMD=python
) else (
    python3 --version >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=*" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
        echo [OK] !PYTHON_VERSION!
        set PYTHON_CMD=python3
    ) else (
        echo [ERROR] Python 3.12+ is required but not found
        echo Please install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

REM Check pip
pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] pip found
    set PIP_CMD=pip
) else (
    pip3 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] pip3 found
        set PIP_CMD=pip3
    ) else (
        echo [ERROR] pip is required but not found
        echo Please install pip
        pause
        exit /b 1
    )
)

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo [OK] Node.js found: !NODE_VERSION!
) else (
    echo [ERROR] Node.js 18+ is required but not found
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check npm
npm --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
    echo [OK] npm found: !NPM_VERSION!
) else (
    echo [ERROR] npm is required but not found
    pause
    exit /b 1
)

REM Check Git
git --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('git --version') do set GIT_VERSION=%%i
    echo [OK] !GIT_VERSION!
) else (
    echo [WARNING] Git not found - optional but recommended for version control
)

echo.
echo All prerequisites met!
echo.

REM Configure API Keys
echo [2/6] Configuring API Keys ^& Integrations...
echo.
echo Claude-Nine uses Anthropic's Claude AI for intelligent agents.
echo You'll need an API key from: https://console.anthropic.com/settings/keys
echo.

REM Check for existing API key
set ANTHROPIC_API_KEY=
if exist "api\.env" (
    findstr /C:"ANTHROPIC_API_KEY" api\.env >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Existing configuration found in api\.env
        set /p USE_EXISTING="Do you want to keep the existing configuration? (y/n): "
        if /i "!USE_EXISTING!"=="y" (
            set KEEP_EXISTING=1
        )
    )
)

REM Prompt for API keys if needed
if not defined KEEP_EXISTING (
    set /p ANTHROPIC_API_KEY="Enter your Anthropic API key (or press Enter to set later): "
    if "!ANTHROPIC_API_KEY!"=="" (
        set ANTHROPIC_API_KEY=your-api-key-here
        echo [WARNING] API key not set. You'll need to update api\.env before using Claude-Nine.
    )

    echo.
    echo Optional Integrations:
    echo You can configure these now or later via the Settings page in the web UI.
    echo.

    REM Azure DevOps
    echo Azure DevOps (press Enter to skip^)
    set /p AZURE_DEVOPS_URL="Azure DevOps URL (e.g., https://dev.azure.com): "
    if not "!AZURE_DEVOPS_URL!"=="" (
        set /p AZURE_DEVOPS_ORGANIZATION="Organization name: "
        set /p AZURE_DEVOPS_TOKEN="Personal Access Token: "
    )
    echo.

    REM Jira
    echo Jira (press Enter to skip^)
    set /p JIRA_URL="Jira URL (e.g., https://yourcompany.atlassian.net): "
    if not "!JIRA_URL!"=="" (
        set /p JIRA_EMAIL="Jira email: "
        set /p JIRA_API_TOKEN="Jira API token: "
    )
    echo.

    REM GitHub
    echo GitHub (press Enter to skip^)
    set /p GITHUB_TOKEN="GitHub Personal Access Token: "
    echo.

    REM Linear
    echo Linear (press Enter to skip^)
    set /p LINEAR_API_KEY="Linear API key: "
    echo.
)

REM Set up API
echo [3/6] Setting Up API Server...
echo.

cd api

REM Create .env file if not keeping existing
if not defined KEEP_EXISTING (
    REM Generate a secure secret key
    for /f "delims=" %%i in ('%PYTHON_CMD% -c "import secrets; print(secrets.token_urlsafe(32))" 2^>nul') do set SECRET_KEY=%%i
    if "!SECRET_KEY!"=="" set SECRET_KEY=change-me-%RANDOM%-%RANDOM%

    echo Creating api\.env configuration...
    (
        echo # Claude-Nine API Configuration (Local Setup^)
        echo.
        echo # Database - SQLite (no cloud database needed^)
        echo DATABASE_URL=sqlite:///./claude_nine.db
        echo.
        echo # Security
        echo SECRET_KEY=!SECRET_KEY!
        echo.
        echo # Anthropic API Key (required for Claude AI^)
        echo ANTHROPIC_API_KEY=!ANTHROPIC_API_KEY!
        echo.
        echo # API Server Settings
        echo API_HOST=0.0.0.0
        echo API_PORT=8000
        echo DEBUG=True
        echo.
        echo # Integration Credentials (Optional^)
        echo # You can also configure these via the Settings page in the web UI
        echo.
        echo # Azure DevOps
        echo AZURE_DEVOPS_URL=!AZURE_DEVOPS_URL!
        echo AZURE_DEVOPS_ORGANIZATION=!AZURE_DEVOPS_ORGANIZATION!
        echo AZURE_DEVOPS_TOKEN=!AZURE_DEVOPS_TOKEN!
        echo.
        echo # Jira
        echo JIRA_URL=!JIRA_URL!
        echo JIRA_EMAIL=!JIRA_EMAIL!
        echo JIRA_API_TOKEN=!JIRA_API_TOKEN!
        echo.
        echo # GitHub
        echo GITHUB_TOKEN=!GITHUB_TOKEN!
        echo.
        echo # Linear
        echo LINEAR_API_KEY=!LINEAR_API_KEY!
    ) > .env

    echo [OK] Configuration file created: api\.env
)

REM Install Python dependencies
echo.
echo Upgrading pip to latest version...
%PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1

echo Installing Python dependencies...
%PIP_CMD% install -r requirements.txt > "%TEMP%\claude-nine-pip-install.log" 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python dependencies installed
) else (
    echo [WARNING] Some issues during pip install. Check %TEMP%\claude-nine-pip-install.log if problems occur.
    echo [WARNING] If you see permission errors, try running as Administrator.
)

cd ..

echo.

REM Set up Dashboard
echo [4/6] Setting Up Dashboard...
echo.

cd dashboard

echo Installing Node.js dependencies (this may take a few minutes^)...
npm install > "%TEMP%\claude-nine-npm-install.log" 2>&1
if %errorlevel% equ 0 (
    echo [OK] Node.js dependencies installed
) else (
    echo [ERROR] npm install failed. Check %TEMP%\claude-nine-npm-install.log for details.
    pause
    exit /b 1
)

cd ..

echo.

REM Create helper scripts
echo [5/6] Creating Helper Scripts...
echo.

REM Create start.bat
(
    echo @echo off
    echo REM Start Claude-Nine (API + Dashboard^)
    echo.
    echo echo Starting Claude-Nine...
    echo echo.
    echo.
    echo REM Start API in background
    echo echo Starting API server on http://localhost:8000...
    echo start /B cmd /c "cd api && %PYTHON_CMD% -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo.
    echo REM Wait for API to start
    echo timeout /t 3 /nobreak ^> nul
    echo.
    echo REM Start Dashboard
    echo echo Starting Dashboard on http://localhost:3000...
    echo cd dashboard
    echo start cmd /c "npm run dev"
    echo cd ..
    echo.
    echo echo.
    echo echo [OK] Claude-Nine is starting up!
    echo echo.
    echo echo   Dashboard: http://localhost:3000
    echo echo   API: http://localhost:8000
    echo echo   API Docs: http://localhost:8000/docs
    echo echo.
    echo echo Press any key to stop servers (or close this window^)
    echo pause ^> nul
    echo.
    echo call stop.bat
) > start.bat

echo [OK] Created start.bat - Run Claude-Nine with: start.bat

REM Create stop.bat
(
    echo @echo off
    echo REM Stop Claude-Nine
    echo.
    echo echo Stopping Claude-Nine...
    echo.
    echo REM Kill API server
    echo for /f "tokens=5" %%%%a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %%%%a 2^>nul
    echo.
    echo REM Kill Dashboard
    echo for /f "tokens=5" %%%%a in ('netstat -aon ^| findstr :3000') do taskkill /F /PID %%%%a 2^>nul
    echo.
    echo echo [OK] Claude-Nine stopped
) > stop.bat

echo [OK] Created stop.bat - Stop Claude-Nine with: stop.bat

REM Create api/run.bat
(
    echo @echo off
    echo REM Run the Claude-Nine API server
    echo.
    echo cd /d "%%~dp0"
    echo.
    echo echo Starting Claude-Nine API...
    echo echo.
    echo echo API will be available at:
    echo echo    - API: http://localhost:8000
    echo echo    - Docs: http://localhost:8000/docs
    echo echo    - Health: http://localhost:8000/health
    echo echo.
    echo.
    echo REM Check if dependencies are installed
    echo python -c "import fastapi" 2^>nul
    echo if errorlevel 1 (
    echo     echo [WARNING] Dependencies not installed. Installing...
    echo     pip install -r requirements.txt
    echo     echo.
    echo ^)
    echo.
    echo REM Run the server
    echo uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) > api\run.bat

echo [OK] Created api\run.bat

echo.

REM Create GETTING_STARTED.md
echo [6/6] Finalizing Installation...
echo.

(
    echo # Getting Started with Claude-Nine
    echo.
    echo ## Quick Start
    echo.
    echo ### Start Claude-Nine
    echo ```batch
    echo start.bat
    echo ```
    echo Or double-click `start.bat` in Windows Explorer.
    echo.
    echo This starts both the API server and dashboard. Open http://localhost:3000 in your browser.
    echo.
    echo ### Stop Claude-Nine
    echo ```batch
    echo stop.bat
    echo ```
    echo.
    echo Or close the terminal windows.
    echo.
    echo ## What's Running?
    echo.
    echo - **Dashboard**: http://localhost:3000 - Your main UI
    echo - **API**: http://localhost:8000 - Backend server
    echo - **API Docs**: http://localhost:8000/docs - Interactive API documentation
    echo.
    echo ## First Steps
    echo.
    echo 1. **Visit the Dashboard**: http://localhost:3000
    echo 2. **Follow the Tutorial**: An interactive tour will guide you through features
    echo 3. **Create Your First Team**:
    echo    - Click "View Teams" → "+ New Team"
    echo    - Add agents to your team
    echo 4. **Add Work Items**:
    echo    - Click "View Work Items" → "+ New Work Item"
    echo    - Or integrate with Azure DevOps/Jira/GitHub
    echo 5. **Assign Work ^& Start**:
    echo    - Use bulk assignment to queue work for your team
    echo    - Start the team and watch your AI agents work!
    echo.
    echo ## Configuration
    echo.
    echo ### API Key
    echo Your Anthropic API key is stored in `api\.env`. To update it:
    echo - Open `api\.env` in Notepad or your favorite editor
    echo - Edit the ANTHROPIC_API_KEY line
    echo.
    echo ### Database
    echo Your data is stored in `api\claude_nine.db` (SQLite file^).
    echo - No cloud database needed
    echo - Portable - just copy the file to backup
    echo.
    echo ## Troubleshooting
    echo.
    echo ### Port Already in Use
    echo If port 8000 or 3000 is already taken:
    echo ```batch
    echo stop.bat
    echo ```
    echo.
    echo ### API Not Starting
    echo Check if your Anthropic API key is set in `api\.env`.
    echo.
    echo ### Dashboard Build Errors
    echo Try clearing node_modules:
    echo ```batch
    echo cd dashboard
    echo rmdir /s /q node_modules
    echo del package-lock.json
    echo npm install
    echo cd ..
    echo ```
    echo.
    echo ## Documentation
    echo.
    echo - **Full Guide**: See `docs\local-setup-guide.md`
    echo - **Bulk Assignment**: See `docs\bulk-assignment-guide.md`
    echo - **API Reference**: http://localhost:8000/docs (when API is running^)
    echo.
    echo ## Where Everything Lives
    echo.
    echo ```
    echo Claude-Nine\
    echo ├── api\                    # Backend (FastAPI^)
    echo │   ├── claude_nine.db      # Your local database
    echo │   ├── .env                # Configuration (API keys^)
    echo │   └── app\                # API code
    echo ├── dashboard\              # Frontend (Next.js^)
    echo │   └── app\                # Dashboard pages
    echo ├── start.bat               # Start Claude-Nine
    echo ├── stop.bat                # Stop Claude-Nine
    echo └── GETTING_STARTED.md      # This file
    echo ```
    echo.
    echo ## Need Help?
    echo.
    echo - Check the tutorial (? icon in dashboard header^)
    echo - Read the docs in `docs\`
    echo - View API documentation at http://localhost:8000/docs
    echo - Check issues at https://github.com/bobum/Claude-Nine/issues
    echo.
    echo ---
    echo.
    echo **Happy coding with your AI development team! 🚀**
) > GETTING_STARTED_WINDOWS.md

echo [OK] Created GETTING_STARTED_WINDOWS.md

echo.
echo ================================================================
echo.
echo  [OK] Installation Complete!
echo.
echo ================================================================
echo.
echo Next Steps:
echo.
echo 1. Start Claude-Nine:
echo    start.bat
echo.
echo 2. Open your browser to:
echo    http://localhost:3000
echo.
echo 3. Follow the interactive tutorial to get started!
echo.
echo Additional Information:
echo.
echo   Quick Guide: GETTING_STARTED_WINDOWS.md
echo   Stop Server: stop.bat
echo   Full Docs: docs\
echo   API Docs: http://localhost:8000/docs (when running^)
echo.

if "!ANTHROPIC_API_KEY!"=="your-api-key-here" (
    echo [WARNING] IMPORTANT: Update your API key in api\.env before starting!
    echo.
)

echo Enjoy your AI development team!
echo.
pause
