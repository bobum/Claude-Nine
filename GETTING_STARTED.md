# Getting Started with Claude-Nine

## Quick Start

### Activate Virtual Environment (Optional)
Claude-Nine uses a Python 3.13 virtual environment to ensure compatibility:
```bash
source activate.sh
```

### Start Claude-Nine
```bash
./start.sh
```

This automatically activates the venv, starts both the API server and dashboard. Open http://localhost:3000 in your browser.

### Stop Claude-Nine
```bash
./stop.sh
```

Or press `Ctrl+C` in the terminal where you ran `./start.sh`.

## What's Running?

- **Dashboard**: http://localhost:3000 - Your main UI
- **API**: http://localhost:8000 - Backend server
- **API Docs**: http://localhost:8000/docs - Interactive API documentation

## Virtual Environment

This installation uses a Python 3.13 virtual environment located in `venv/`.

Benefits:
- Isolated from your system Python
- Uses Python 3.13 (required for CrewAI compatibility)
- All dependencies installed separately from your global Python

To manually activate:
```bash
source venv/bin/activate  # Linux/Mac
source venv/Scripts/activate  # Git Bash on Windows
```

To deactivate:
```bash
deactivate
```

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
Your Anthropic API key is stored in `api/.env`. To update it:
```bash
nano api/.env  # or use your favorite editor
# Edit the ANTHROPIC_API_KEY line
```

### Database
Your data is stored in `api/claude_nine.db` (SQLite file).
- No cloud database needed
- Portable - just copy the file to backup
- View with: `sqlite3 api/claude_nine.db`

## Troubleshooting

### Port Already in Use
If port 8000 or 3000 is already taken:
```bash
# Kill existing process
./stop.sh

# Or manually:
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### API Not Starting
Check if your Anthropic API key is set in `api/.env`.

### Dashboard Build Errors
Try clearing node_modules:
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
cd ..
```

### Python Version Issues
This installation requires Python 3.13 for CrewAI compatibility. If you see import errors:
1. Verify you're using the venv: `source activate.sh`
2. Check Python version: `python --version` (should be 3.13.x)
3. Reinstall dependencies: `pip install -r api/requirements.txt -r claude-multi-agent-orchestrator/requirements.txt`

## Documentation

- **Full Guide**: See `docs/local-setup-guide.md`
- **Bulk Assignment**: See `docs/bulk-assignment-guide.md`
- **API Reference**: http://localhost:8000/docs (when API is running)

## Where Everything Lives

```
Claude-Nine/
├── venv/                   # Python 3.13 virtual environment
├── api/                    # Backend (FastAPI)
│   ├── claude_nine.db      # Your local database
│   ├── .env                # Configuration (API keys)
│   └── app/                # API code
├── dashboard/              # Frontend (Next.js)
│   └── app/                # Dashboard pages
├── claude-multi-agent-orchestrator/  # CrewAI orchestrator
├── start.sh                # Start Claude-Nine
├── stop.sh                 # Stop Claude-Nine
├── activate.sh             # Activate Python venv
└── GETTING_STARTED.md      # This file
```

## Need Help?

- Check the tutorial (? icon in dashboard header)
- Read the docs in `docs/`
- View API documentation at http://localhost:8000/docs
- Check issues at https://github.com/bobum/Claude-Nine/issues

---

**Happy coding with your AI development team! 🚀**
