#!/bin/bash
# Start the Resilience Architect Backend API

cd agent_backend
source .venv/bin/activate
uv run api.py
