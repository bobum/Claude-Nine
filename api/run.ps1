# Run the Claude-Nine API server

Set-Location $PSScriptRoot

Write-Host "🚀 Starting Claude-Nine API..." -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 API will be available at:"
Write-Host "   - API: http://localhost:8000"
Write-Host "   - Docs: http://localhost:8000/docs"
Write-Host "   - Health: http://localhost:8000/health"
Write-Host ""

# Check if dependencies are installed
try {
    python -c "import fastapi" 2>$null
    if ($LASTEXITCODE -ne 0) {
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
