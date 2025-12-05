#!/bin/bash

# Stop Claude-Nine - stops all services and cleans up

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Claude-Nine...${NC}"
echo ""

# Kill Dashboard
DASH_PIDS=$(pgrep -f "next start" 2>/dev/null || pgrep -f "next dev" 2>/dev/null)
if [ ! -z "$DASH_PIDS" ]; then
    echo "Stopping Dashboard (PIDs: $DASH_PIDS)..."
    pkill -f "next start" 2>/dev/null
    pkill -f "next dev" 2>/dev/null
    pkill -f "node.*next" 2>/dev/null
    sleep 1
    pkill -9 -f "next start" 2>/dev/null
    pkill -9 -f "next dev" 2>/dev/null
    pkill -9 -f "node.*next" 2>/dev/null
else
    echo "Dashboard not running"
fi

# Kill Celery workers
CELERY_PIDS=$(pgrep -f "celery.*worker" 2>/dev/null)
if [ ! -z "$CELERY_PIDS" ]; then
    echo "Stopping Celery workers (PIDs: $CELERY_PIDS)..."
    pkill -f "celery.*worker" 2>/dev/null
    sleep 1
    pkill -9 -f "celery.*worker" 2>/dev/null
else
    echo "Celery workers not running"
fi

# Kill API server
API_PIDS=$(pgrep -f "uvicorn app.main:app" 2>/dev/null)
if [ ! -z "$API_PIDS" ]; then
    echo "Stopping API server (PIDs: $API_PIDS)..."
    pkill -f "uvicorn app.main:app" 2>/dev/null
    sleep 1
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null
else
    echo "API server not running"
fi

# Stop Redis container if we started one
if command -v docker &> /dev/null; then
    REDIS_CONTAINER=$(docker ps -q -f name=claude-nine-redis 2>/dev/null)
    if [ ! -z "$REDIS_CONTAINER" ]; then
        echo "Stopping Redis container..."
        docker stop claude-nine-redis >/dev/null 2>&1 || true
        docker rm claude-nine-redis >/dev/null 2>&1 || true
    else
        echo "Redis container not running"
    fi
fi

echo ""
echo -e "${GREEN}✓ Claude-Nine stopped${NC}"
