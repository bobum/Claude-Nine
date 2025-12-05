# Stop Claude-Nine Services

Gracefully stop all Claude-Nine services (API, Dashboard, and any running orchestrators).

## Instructions

1. **Stop the API server**:
   ```bash
   # Find and kill uvicorn process
   # Linux/Mac:
   pkill -f "uvicorn app.main:app"
   # OR find PID:
   lsof -i :8000
   kill -9 <PID>

   # Windows:
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

2. **Stop the Dashboard**:
   ```bash
   # Find and kill Next.js process
   # Linux/Mac:
   pkill -f "next"
   # OR:
   lsof -i :3001
   kill -9 <PID>

   # Windows:
   netstat -ano | findstr :3001
   taskkill /PID <PID> /F
   ```

3. **Stop any running orchestrators**:
   ```bash
   # Linux/Mac:
   pkill -f "orchestrator.py"

   # Windows:
   taskkill /IM python.exe /F  # Caution: kills all Python processes
   ```

4. **Verify all stopped**:
   ```bash
   # These should fail or show nothing:
   curl http://localhost:8000/health
   curl http://localhost:3001
   ```

## Quick Stop (Single Command)

If `stop.sh` exists in the project root:
```bash
./stop.sh
```

## Emergency Kill All

If services are unresponsive:
```bash
# Linux/Mac - Kill all related processes
pkill -9 -f "uvicorn"
pkill -9 -f "next"
pkill -9 -f "orchestrator"

# Windows
taskkill /F /IM uvicorn.exe
taskkill /F /IM node.exe
```

## Verify Clean Shutdown

```bash
# Check no processes on ports
lsof -i :8000  # Should be empty
lsof -i :3001  # Should be empty

# Check no orchestrator processes
ps aux | grep orchestrator  # Should only show grep itself
```
