# Migration Notes - Textual to Ink

## What Changed

### Fixed Import Errors
The original `resilience_agent/tools/__init__.py` was importing non-existent modules:
- ❌ `fis_service_tools` (doesn't exist)
- ❌ `experiment_template_tools` (doesn't exist)

**Fix Applied:**
Updated to only import available modules:
- ✅ `planning_tools`
- ✅ `operation_modes`

### Dependency Management
The project uses **uv** for Python dependency management (faster than pip).

**Start scripts updated to use:**
```bash
uv run api.py  # Instead of python api.py
```

### Architecture Changes

```
Before:                          After:
┌─────────────────┐             ┌─────────────────┐
│   main.py       │             │ agent_frontend/ │
│  (Textual TUI)  │             │   (Ink TUI)     │
│                 │             └────────┬────────┘
│  ┌──────────┐   │                      │ HTTP
│  │ Agent    │   │                      ▼
│  └──────────┘   │             ┌─────────────────┐
└─────────────────┘             │ agent_backend/  │
                                │   api.py        │
                                │  (FastAPI)      │
                                │  ┌──────────┐   │
                                │  │ Agent    │   │
                                │  └──────────┘   │
                                └─────────────────┘
```

**Benefits:**
- Separation of concerns (UI vs Logic)
- Can run backend independently
- Could add web UI later
- Easier testing of API endpoints

### UI Interaction Changes

| Feature | Old (Textual) | New (Ink) |
|---------|---------------|-----------|
| Show LLM info | `i` key | `/info` command |
| Clear chat | `Ctrl+L` | `/clear` command |
| Quit app | `q` or `Ctrl+C` | `/quit` or `/exit` |
| Help | N/A | `/help` command |
| Check mode | N/A | `/mode` command |

### File Locations

**Moved to `agent_backend/`:**
- All Python agent code
- `main.py` (deprecated Textual TUI)
- Virtual environment (`.venv`)
- Dependencies

**Created `agent_frontend/`:**
- Ink-based TUI in TypeScript/React
- Modern terminal UI with slash commands
- Communicates via REST API

**Root directory:**
- `.env` (environment variables)
- `README.md` (updated documentation)
- `QUICKSTART.md` (quick setup guide)
- Helper scripts: `start-backend.sh`, `start-frontend.sh`

## Setup Instructions

### 1. Install uv (if not installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Backend Setup
```bash
cd agent_backend
uv sync  # Installs all dependencies
```

### 3. Frontend Setup
```bash
cd agent_frontend
bun install  # Or: npm install
```

### 4. Run the Application

**Terminal 1:**
```bash
./start-backend.sh
```

**Terminal 2:**
```bash
./start-frontend.sh
```

## Common Issues & Solutions

### Issue: Import errors on startup

**Symptom:**
```
ModuleNotFoundError: No module named 'resilience_agent.tools.fis_service_tools'
```

**Solution:**
This has been fixed in the latest version. The `__init__.py` now only imports existing modules.

### Issue: Dependencies not installed

**Symptom:**
```
ModuleNotFoundError: No module named 'strands_tools'
```

**Solution:**
```bash
cd agent_backend
uv sync
```

### Issue: Wrong virtual environment warning

**Symptom:**
```
warning: `VIRTUAL_ENV=/some/other/path` does not match the project environment
```

**Solution:**
This is safe to ignore. The `uv run` command manages the environment automatically.
Or, use the project's venv:
```bash
cd agent_backend
source .venv/bin/activate
python api.py
```

## API Endpoints

The backend exposes three main endpoints:

### 1. Health Check
```bash
curl http://localhost:8000/api/health
```

### 2. Send Message
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List EC2 instances",
    "sessionId": "test-session"
  }'
```

### 3. Get Info
```bash
curl http://localhost:8000/api/info
```

## Development

### Backend Development
```bash
cd agent_backend
uv run uvicorn api:app --reload
```

### Frontend Development
```bash
cd agent_frontend
bun run dev
```

## Rollback to Textual TUI

If you need to use the old Textual-based TUI:

```bash
cd agent_backend
source .venv/bin/activate
python main.py
```

Note: This doesn't use the API and runs the agent directly in the TUI.

## Next Steps

- [ ] Test mode transitions with new TUI
- [ ] Verify AWS resource discovery works
- [ ] Test experiment planning workflows
- [ ] Add session persistence to API
- [ ] Implement token usage tracking in API
- [ ] Add WebSocket support for streaming responses
