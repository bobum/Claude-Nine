#!/bin/bash

# Start Claude-Nine (Redis + API + Worker + Dashboard)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Starting Claude-Nine             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Create logs directory
mkdir -p logs

# Track what we started (for cleanup on Ctrl+C)
REDIS_CONTAINER=""
API_PID=""
WORKER_PID=""
DASHBOARD_PID=""

cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping Claude-Nine...${NC}"

    # Stop Dashboard
    if [ ! -z "$DASHBOARD_PID" ] && kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo "Stopping Dashboard..."
        kill $DASHBOARD_PID 2>/dev/null || true
    fi

    # Stop Celery Worker
    if [ ! -z "$WORKER_PID" ] && kill -0 $WORKER_PID 2>/dev/null; then
        echo "Stopping Celery Worker..."
        kill $WORKER_PID 2>/dev/null || true
    fi

    # Stop API
    if [ ! -z "$API_PID" ] && kill -0 $API_PID 2>/dev/null; then
        echo "Stopping API..."
        kill $API_PID 2>/dev/null || true
    fi

    # Stop Redis container if we started it
    if [ ! -z "$REDIS_CONTAINER" ]; then
        echo "Stopping Redis container..."
        docker stop $REDIS_CONTAINER >/dev/null 2>&1 || true
        docker rm $REDIS_CONTAINER >/dev/null 2>&1 || true
    fi

    echo -e "${GREEN}✓ Claude-Nine stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

#######################################
# Activate virtual environment
#######################################
echo -e "${YELLOW}[1/5] Activating virtual environment...${NC}"

if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo -e "${RED}✗ Virtual environment not found. Run ./install.sh first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment activated${NC}"

#######################################
# Start Redis
#######################################
echo ""
echo -e "${YELLOW}[2/5] Starting Redis...${NC}"

# Check if Redis is already running
if command -v redis-cli &> /dev/null && redis-cli ping &> /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is already running${NC}"
# Try Docker
elif command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
    # Check if a Redis container is already running
    EXISTING=$(docker ps -q -f name=claude-nine-redis 2>/dev/null)
    if [ ! -z "$EXISTING" ]; then
        echo -e "${GREEN}✓ Redis container already running${NC}"
        REDIS_CONTAINER=""
    else
        # Remove any stopped container with same name
        docker rm claude-nine-redis >/dev/null 2>&1 || true

        echo "Starting Redis container..."
        REDIS_CONTAINER=$(docker run -d --name claude-nine-redis -p 6379:6379 redis:alpine)

        # Wait for Redis to be ready
        for i in {1..10}; do
            if docker exec $REDIS_CONTAINER redis-cli ping >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Redis container started${NC}"
                break
            fi
            sleep 0.5
        done
    fi
else
    echo -e "${RED}✗ Redis is not available${NC}"
    echo ""
    echo "  Please either:"
    echo "  1. Start Redis manually: redis-server"
    echo "  2. Start Docker and run: docker run -d -p 6379:6379 redis:alpine"
    echo ""
    exit 1
fi

#######################################
# Start API
#######################################
echo ""
echo -e "${YELLOW}[3/5] Starting API server...${NC}"

cd api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/api.log 2>&1 &
API_PID=$!
cd ..

# Wait for API to be ready
echo -n "Waiting for API"
for i in {1..30}; do
    if ! kill -0 $API_PID 2>/dev/null; then
        echo ""
        echo -e "${RED}✗ API process died${NC}"
        echo "Last 20 lines of logs/api.log:"
        tail -n 20 logs/api.log
        cleanup
        exit 1
    fi

    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ API server ready (PID: $API_PID)${NC}"
        break
    fi

    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo ""
    echo -e "${RED}✗ API failed to respond${NC}"
    tail -n 20 logs/api.log
    cleanup
    exit 1
fi

#######################################
# Start Celery Worker
#######################################
echo ""
echo -e "${YELLOW}[4/5] Starting Celery worker...${NC}"

cd api

# Determine pool type based on OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows: use solo pool (threads don't work well)
    celery -A app.celery_app:celery_app worker -Q orchestrator -c 1 -l INFO --pool=solo > ../logs/worker.log 2>&1 &
else
    # Linux/Mac: use prefork pool
    celery -A app.celery_app:celery_app worker -Q orchestrator -c 4 -l INFO > ../logs/worker.log 2>&1 &
fi
WORKER_PID=$!
cd ..

sleep 2

if kill -0 $WORKER_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Celery worker started (PID: $WORKER_PID)${NC}"
else
    echo -e "${RED}✗ Celery worker failed to start${NC}"
    echo "Last 20 lines of logs/worker.log:"
    tail -n 20 logs/worker.log
    cleanup
    exit 1
fi

#######################################
# Start Dashboard
#######################################
echo ""
echo -e "${YELLOW}[5/5] Starting Dashboard...${NC}"

cd dashboard

# Build if needed
if [ ! -d ".next" ]; then
    echo "Building dashboard (first run)..."
    npm run build > ../logs/dashboard-build.log 2>&1
fi

PORT=3001 npm start > ../logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
cd ..

# Wait for Dashboard to be ready
echo -n "Waiting for Dashboard"
for i in {1..30}; do
    if ! kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo ""
        echo -e "${RED}✗ Dashboard process died${NC}"
        tail -n 20 logs/dashboard.log
        cleanup
        exit 1
    fi

    if curl -s http://localhost:3001 > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ Dashboard ready (PID: $DASHBOARD_PID)${NC}"
        break
    fi

    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo ""
    echo -e "${RED}✗ Dashboard failed to respond${NC}"
    tail -n 20 logs/dashboard.log
    cleanup
    exit 1
fi

#######################################
# Success!
#######################################
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Claude-Nine is running!            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "  Dashboard:  http://localhost:3001"
echo "  API:        http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo ""
echo "  Logs:"
echo "    API:       logs/api.log"
echo "    Worker:    logs/worker.log"
echo "    Dashboard: logs/dashboard.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for Ctrl+C
wait
