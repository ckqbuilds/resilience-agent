# Quick Start Guide

## First Time Setup

### 1. Install Bun (if not already installed)
```bash
curl -fsSL https://bun.sh/install | bash
```

### 2. Configure Environment
Create a `.env` file in the project root:
```env
ANTHROPIC_API_KEY=sk-ant-...
AWS_PROFILE=default
AWS_REGION=us-east-1
```

### 3. Setup Backend

The backend uses `uv` for dependency management:

```bash
cd agent_backend
uv sync  # Installs all dependencies and creates venv
```

Alternatively, use pip:
```bash
cd agent_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Setup Frontend
```bash
cd agent_frontend
bun install
```

## Running the Application

### Option 1: Using Scripts (Easiest)

**Terminal 1 - Start Backend:**
```bash
./start-backend.sh
```

**Terminal 2 - Start Frontend:**
```bash
./start-frontend.sh
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd agent_backend
uv run api.py
# API starts on http://localhost:8000
```

Or with activated venv:
```bash
cd agent_backend
source .venv/bin/activate
python api.py
```

**Terminal 2 - Frontend:**
```bash
cd agent_frontend
bun start
```

## First Commands to Try

Once the TUI is running:

1. `/help` - See all available commands
2. `/info` - View system information
3. Try asking: "What AWS resources can you discover?"
4. `/mode` - Check current operation mode
5. `/quit` - Exit when done

## Troubleshooting

**Backend won't start?**
- Check Python version: `python --version` (need 3.13+)
- Install dependencies: `cd agent_backend && uv sync`
- Or with pip: `source agent_backend/.venv/bin/activate && pip install -r agent_backend/requirements.txt`
- Check for import errors: Run `uv run python -c "from resilience_agent.agent import resilience_agent"`

**Frontend can't connect?**
- Verify backend is running: `curl http://localhost:8000/api/health`
- Check port 8000 isn't in use: `lsof -i :8000`

**Bun not found?**
- Install: `curl -fsSL https://bun.sh/install | bash`
- Or use npm: `cd agent_frontend && npm install && npm start`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the [API endpoints](README.md#api-endpoints)
- Learn about [operation modes](README.md#operation-modes)
