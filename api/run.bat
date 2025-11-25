@echo off
REM Run the Claude-Nine API server

cd /d "%~dp0"

echo Starting Claude-Nine API...
echo.
echo API will be available at:
echo    - API: http://localhost:8000
echo    - Docs: http://localhost:8000/docs
echo    - Health: http://localhost:8000/health
echo.

REM Check if dependencies are installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [WARNING] Dependencies not installed. Installing...
    pip install -r requirements.txt
    echo.
)

REM Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
