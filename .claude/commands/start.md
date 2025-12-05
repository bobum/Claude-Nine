# Start Claude-Nine Services

Start the complete Claude-Nine stack (API + Dashboard) with health checks.

## Instructions

1. **Check prerequisites first**:
   - Ensure Python 3.12+ is available
   - Ensure Node.js 18+ is available
   - Verify the virtual environment exists at `venv/`

2. **Start the API server**:
   ```bash
   cd api
   source ../venv/bin/activate  # Linux/Mac
   # OR: . ../venv/Scripts/activate  # Windows
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Wait for API health check**:
   ```bash
   # Poll until ready (may take 5-10 seconds)
   curl http://localhost:8000/health
   curl http://localhost:8000/health/db
   ```

4. **Start the Dashboard**:
   ```bash
   cd dashboard
   npm run dev
   ```

5. **Verify both services**:
   - API: http://localhost:8000/health
   - Dashboard: http://localhost:3001

## Expected Output

```
API Server:
  INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
  INFO:     Started reloader process [12345]
  INFO:     Started server process [12346]
  INFO:     Waiting for application startup.
  INFO:     Application startup complete.

Dashboard:
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3001
  - Environments: .env.local
  ✓ Ready in XXXms
```

## Quick Start (Single Command)

If `start.sh` exists in the project root:
```bash
./start.sh
```

## Troubleshooting

- **Port 8000 in use**: Kill existing process with `lsof -i :8000` then `kill -9 <PID>`
- **Port 3001 in use**: Kill existing process with `lsof -i :3001` then `kill -9 <PID>`
- **venv not found**: Run `python -m venv venv` then `pip install -r api/requirements.txt`
- **npm packages missing**: Run `cd dashboard && npm install`
