#!/bin/bash
# Run the Claude-Nine API server

cd "$(dirname "$0")"

echo "🚀 Starting Claude-Nine API..."
echo ""
echo "📍 API will be available at:"
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Health: http://localhost:8000/health"
echo ""

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Dependencies not installed. Installing..."
    pip install -r requirements.txt
    echo ""
fi

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
