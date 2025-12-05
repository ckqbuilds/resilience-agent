#!/usr/bin/env python3
import sys
sys.path.insert(0, 'agent_backend')

# Simple file change to invoke push

try:
    from resilience_agent.agent import resilience_agent, mode_state
    print("✓ Import successful!")
    print(f"✓ Agent name: {resilience_agent.name}")
    print(f"✓ Current mode: {mode_state.current_mode.name}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
