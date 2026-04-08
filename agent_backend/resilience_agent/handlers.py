"""Event capturing handlers for agent tool call visibility.

This module provides callback handlers that capture agent events (tool calls, results)
for display in the frontend without requiring streaming architecture.
"""

from typing import List, Dict, Any
from datetime import datetime


class EventCapturingHandler:
    """Captures agent events for frontend display.

    This handler implements the Strands callback handler protocol by providing
    a __call__ method that receives event data via kwargs.
    """

    def __init__(self):
        """Initialize the event handler with an empty events list."""
        self.events: List[Dict[str, Any]] = []
        self.current_tool = None

    def __call__(self, **kwargs: Any) -> None:
        """Callback method invoked by Strands agent during execution.

        Args:
            **kwargs: Event data including:
                - current_tool_use: Dict with tool call information
                - data: Text content being streamed
                - complete: Whether response is complete
        """
        # Capture tool calls
        current_tool_use = kwargs.get("current_tool_use", {})

        if current_tool_use and current_tool_use.get("name"):
            # New tool call detected
            if self.current_tool != current_tool_use:
                self.current_tool = current_tool_use

                self.events.append({
                    "type": "tool_call_start",
                    "tool_name": current_tool_use.get("name"),
                    "tool_input": current_tool_use.get("input", {}),
                    "timestamp": datetime.now().isoformat()
                })

    def get_events(self) -> List[Dict[str, Any]]:
        """Return captured events.

        Returns:
            List of event dictionaries
        """
        return self.events

    def clear(self):
        """Reset events for new message."""
        self.events = []
        self.current_tool = None

    def get_summary(self) -> str:
        """Get a human-readable summary of captured events.

        Returns:
            Formatted summary string
        """
        tool_calls = [e for e in self.events if e["type"] == "tool_call_start"]
        errors = [e for e in self.events if e["type"] == "tool_call_error"]

        summary = f"Captured {len(tool_calls)} tool calls"
        if errors:
            summary += f", {len(errors)} errors"

        return summary
