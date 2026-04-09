"""Operation Modes for Resilience Agent.

This module implements a three-tier operation mode system (Planning, Action, Execution)
with human-in-the-loop approvals for mode transitions using Strands SDK hooks.
"""

from enum import Enum, auto
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeInvocationEvent, AfterInvocationEvent, BeforeToolCallEvent, AfterToolCallEvent


class OperationMode(Enum):
    """Three operation modes with increasing danger levels."""
    PLANNING = auto()    # Default, safe operations only
    ACTION = auto()      # Build/create templates and queues
    EXECUTION = auto()   # Actually run FIS experiments

    def __str__(self) -> str:
        return self.name

    @property
    def description(self) -> str:
        """Human-readable description of the mode."""
        descriptions = {
            OperationMode.PLANNING: "Safe discovery and planning mode",
            OperationMode.ACTION: "Template creation and queuing mode",
            OperationMode.EXECUTION: "Experiment execution mode (DANGEROUS)"
        }
        return descriptions[self]

    @property
    def color(self) -> str:
        """Color for TUI display."""
        colors = {
            OperationMode.PLANNING: "green",
            OperationMode.ACTION: "yellow",
            OperationMode.EXECUTION: "red"
        }
        return colors[self]


class RiskLevel(Enum):
    """Risk classification for tool operations."""
    SAFE = auto()        # Read-only, no state changes
    MEDIUM = auto()      # Creates resources but doesn't execute
    HIGH = auto()        # Executes experiments or destructive ops
    UNKNOWN = auto()     # Cannot determine risk level


@dataclass
class ModeTransition:
    """Record of a mode transition."""
    from_mode: OperationMode
    to_mode: OperationMode
    timestamp: datetime = field(default_factory=datetime.now)
    approved_by: str = "system"  # or "user"
    reason: str = ""


class ToolRiskClassifier:
    """Classifies tool calls by risk level to determine required operation mode."""

    # AWS operation patterns that are safe (read-only)
    SAFE_AWS_PATTERNS = [
        "describe_", "list_", "get_", "search_", "query_",
        "lookup_", "fetch_", "read_", "head_", "view_"
    ]

    # AWS operations that create/modify but don't execute
    MEDIUM_AWS_PATTERNS = [
        "create_experiment_template", "update_experiment_template",
        "create_", "put_", "update_", "modify_", "register_",
        "tag_", "untag_", "associate_", "disassociate_"
    ]

    # AWS operations that execute experiments or are destructive
    HIGH_AWS_PATTERNS = [
        "start_experiment", "run_", "execute_", "invoke_",
        "delete_", "terminate_", "stop_", "kill_", "destroy_",
        "reboot_", "reset_"
    ]

    # Specific FIS operations mapping
    FIS_OPERATION_RISK = {
        "list_experiments": RiskLevel.SAFE,
        "get_experiment": RiskLevel.SAFE,
        "list_experiment_templates": RiskLevel.SAFE,
        "get_experiment_template": RiskLevel.SAFE,
        "create_experiment_template": RiskLevel.MEDIUM,
        "update_experiment_template": RiskLevel.MEDIUM,
        "start_experiment": RiskLevel.HIGH,
        "stop_experiment": RiskLevel.HIGH,
        "delete_experiment_template": RiskLevel.MEDIUM,
    }

    # Expected services per mode for context-aware classification
    PLANNING_SERVICES = [
        "resource-explorer-2", "config", "cloudformation", "cloudwatch",
        "ec2", "rds", "lambda", "ecs", "elasticloadbalancing",
        "elasticloadbalancingv2", "autoscaling", "s3"
    ]

    ACTION_SERVICES = [
        "fis", "iam", "logs", "sns", "sqs"
    ]

    EXECUTION_SERVICES = [
        "fis"  # For starting experiments
    ]

    @classmethod
    def classify_tool_call(cls, tool_name: str, tool_input: Dict[str, Any],
                          current_mode: OperationMode = OperationMode.PLANNING) -> RiskLevel:
        """Classify a tool call by risk level.

        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters to the tool
            current_mode: Current operation mode for context-aware classification

        Returns:
            RiskLevel enum value
        """
        # Handle use_aws tool specially
        if tool_name == "use_aws":
            return cls._classify_aws_operation(
                tool_input.get("service_name", ""),
                tool_input.get("operation_name", ""),
                current_mode
            )

        # Direct FIS tools (legacy, but still classify)
        if tool_name == "start_experiment":
            return RiskLevel.HIGH

        if tool_name in ["create_experiment_template", "update_experiment_template"]:
            return RiskLevel.MEDIUM

        if tool_name in ["list_all_fis_experiments", "get_experiment_details",
                         "list_experiment_templates", "get_experiment_template"]:
            return RiskLevel.SAFE

        # Discovery agent and knowledge agent are always safe
        if tool_name in ["discovery_agent", "aws_knowledge_agent"]:
            return RiskLevel.SAFE

        # Resource explorer tools are safe
        if tool_name in ["list_views", "search_resources", "discover_relationships"]:
            return RiskLevel.SAFE

        if tool_name == "create_view":
            return RiskLevel.MEDIUM

        # Planning tools are safe (read-only or just saving to disk)
        if tool_name in ["save_experiment_plan", "load_experiment_plan", "list_experiment_plans",
                         "get_plan_summary", "export_plan_to_fis_template"]:
            return RiskLevel.SAFE

        # Deleting plans is medium risk (modifying state)
        if tool_name == "delete_experiment_plan":
            return RiskLevel.MEDIUM

        # Default to unknown for safety
        return RiskLevel.UNKNOWN

    @classmethod
    def _classify_aws_operation(cls, service_name: str, operation_name: str,
                                current_mode: OperationMode) -> RiskLevel:
        """Classify AWS operation by service and operation name with context awareness.

        Args:
            service_name: AWS service name (e.g., 'fis', 'ec2')
            operation_name: Operation name (e.g., 'start_experiment')
            current_mode: Current mode for context-aware classification

        Returns:
            RiskLevel based on operation and context
        """
        # FIS service gets special handling
        if service_name == "fis":
            return cls.FIS_OPERATION_RISK.get(operation_name, RiskLevel.UNKNOWN)

        # Check safe patterns first (read-only operations)
        for pattern in cls.SAFE_AWS_PATTERNS:
            if operation_name.startswith(pattern):
                # Even safe operations on unexpected services might be suspicious
                if current_mode == OperationMode.PLANNING:
                    if service_name in cls.PLANNING_SERVICES:
                        return RiskLevel.SAFE
                    # Unknown service in planning mode escalates to ACTION
                    return RiskLevel.UNKNOWN
                return RiskLevel.SAFE

        # Check high-risk patterns
        for pattern in cls.HIGH_AWS_PATTERNS:
            if operation_name.startswith(pattern):
                return RiskLevel.HIGH

        # Check medium-risk patterns
        for pattern in cls.MEDIUM_AWS_PATTERNS:
            if operation_name.startswith(pattern):
                # Template creation is medium risk
                if service_name == "fis":
                    return RiskLevel.MEDIUM
                # Other creation operations
                return RiskLevel.MEDIUM

        # Default to unknown (context-dependent escalation)
        return RiskLevel.UNKNOWN

    @classmethod
    def get_required_mode(cls, risk_level: RiskLevel,
                         current_mode: OperationMode = OperationMode.PLANNING) -> OperationMode:
        """Get the minimum operation mode required for a given risk level.

        Args:
            risk_level: The risk level of the operation
            current_mode: Current mode for context-aware escalation

        Returns:
            Required operation mode
        """
        if risk_level == RiskLevel.SAFE:
            return OperationMode.PLANNING
        elif risk_level == RiskLevel.MEDIUM:
            return OperationMode.ACTION
        elif risk_level == RiskLevel.HIGH:
            return OperationMode.EXECUTION
        else:  # UNKNOWN
            # Context-aware escalation
            if current_mode == OperationMode.PLANNING:
                return OperationMode.ACTION  # Escalate to ACTION from PLANNING
            elif current_mode == OperationMode.ACTION:
                return OperationMode.EXECUTION  # Escalate to EXECUTION from ACTION
            else:
                return OperationMode.EXECUTION  # Already in EXECUTION, stay there


class ModeState:
    """Singleton class managing the current operation mode.

    Thread-safe state manager for the application's operation mode.
    Shared between the agent hook system and the TUI.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._current_mode = OperationMode.PLANNING
        self._mode_history: List[ModeTransition] = []
        self._mode_stack: List[OperationMode] = []  # For tracking elevations
        self._transition_in_progress = False
        self._pending_transition: Optional[Tuple[OperationMode, str]] = None
        self._initialized = True

    @property
    def current_mode(self) -> OperationMode:
        """Get the current operation mode."""
        with self._lock:
            return self._current_mode

    def request_mode_transition(self, to_mode: OperationMode, reason: str = "") -> bool:
        """Request a mode transition (requires approval via interrupt).

        Args:
            to_mode: Target operation mode
            reason: Reason for the transition

        Returns:
            True if transition is allowed without approval, False if approval needed
        """
        with self._lock:
            # Transitioning to a less dangerous mode doesn't need approval
            if to_mode.value < self._current_mode.value:
                self._transition_to(to_mode, reason, "system")
                return True

            # Same mode - no transition needed
            if to_mode == self._current_mode:
                return True

            # More dangerous mode - needs approval
            self._pending_transition = (to_mode, reason)
            return False

    def approve_transition(self, approved: bool, user: str = "user") -> None:
        """Approve or reject a pending mode transition."""
        with self._lock:
            if self._pending_transition is None:
                return

            if approved:
                to_mode, reason = self._pending_transition
                self._transition_to(to_mode, reason, user)

            self._pending_transition = None

    def _transition_to(self, to_mode: OperationMode, reason: str, user: str) -> None:
        """Internal method to perform the actual transition."""
        # Push current mode to stack for later restoration (if elevating)
        if to_mode.value > self._current_mode.value:
            self._mode_stack.append(self._current_mode)

        transition = ModeTransition(
            from_mode=self._current_mode,
            to_mode=to_mode,
            approved_by=user,
            reason=reason
        )
        self._mode_history.append(transition)
        self._current_mode = to_mode

    def revert_mode(self) -> None:
        """Revert to previous mode after operation completes."""
        with self._lock:
            if self._mode_stack:
                previous_mode = self._mode_stack.pop()
                if previous_mode != self._current_mode:
                    transition = ModeTransition(
                        from_mode=self._current_mode,
                        to_mode=previous_mode,
                        approved_by="system",
                        reason="Automatic revert after operation"
                    )
                    self._mode_history.append(transition)
                    self._current_mode = previous_mode

    def reset_to_planning(self) -> None:
        """Reset to planning mode (called on app startup)."""
        with self._lock:
            if self._current_mode != OperationMode.PLANNING:
                self._transition_to(
                    OperationMode.PLANNING,
                    "Application startup",
                    "system"
                )
            # Clear the stack on reset
            self._mode_stack.clear()

    @property
    def pending_transition(self) -> Optional[Tuple[OperationMode, str]]:
        """Get pending transition if any."""
        with self._lock:
            return self._pending_transition

    def can_execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check if a tool can be executed in the current mode.

        Returns:
            (can_execute, reason_if_blocked)
        """
        with self._lock:
            risk_level = ToolRiskClassifier.classify_tool_call(
                tool_name, tool_input, self._current_mode
            )
            required_mode = ToolRiskClassifier.get_required_mode(risk_level, self._current_mode)

            if required_mode.value <= self._current_mode.value:
                return True, None

            reason = (f"Tool '{tool_name}' requires {required_mode.name} mode, "
                     f"currently in {self._current_mode.name} mode")
            return False, reason


class OperationModeHook(HookProvider):
    """Hook provider that enforces operation mode restrictions on tool calls."""

    def __init__(self, mode_state: ModeState, read_only: bool = False):
        self.mode_state = mode_state
        self.read_only = read_only

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register hook callbacks."""
        registry.add_callback(BeforeInvocationEvent, self.on_invocation_start)
        registry.add_callback(BeforeToolCallEvent, self.on_before_tool_call)
        registry.add_callback(AfterInvocationEvent, self.on_invocation_end)

    def on_invocation_start(self, event: BeforeInvocationEvent) -> None:
        """Called at the start of each agent invocation."""
        # Log the current mode for debugging
        mode_status = "READ-ONLY" if self.read_only else "transitions allowed"
        print(f"[DEBUG] Agent invocation starting in {self.mode_state.current_mode.name} mode ({mode_status})")

    def on_before_tool_call(self, event: BeforeToolCallEvent) -> None:
        """Intercept tool calls to enforce operation mode restrictions.

        This is the critical hook that:
        1. Classifies the tool call's risk level
        2. Checks if current mode permits the operation
        3. Raises interrupt for mode transition approval if needed
        4. Cancels the tool if not permitted or in read-only mode
        """
        if event.selected_tool is None:
            return

        tool_name = event.tool_use["name"]
        tool_input = event.tool_use.get("input", {})

        # Classify the tool call
        risk_level = ToolRiskClassifier.classify_tool_call(
            tool_name, tool_input, self.mode_state.current_mode
        )
        required_mode = ToolRiskClassifier.get_required_mode(
            risk_level, self.mode_state.current_mode
        )
        current_mode = self.mode_state.current_mode

        # Check if we can execute in current mode
        if required_mode.value <= current_mode.value:
            # Tool is permitted in current mode
            return

        # Tool requires a higher mode
        reason = (f"Tool '{tool_name}' requires {required_mode.name} mode "
                 f"(risk: {risk_level.name})")

        # If in read-only mode, immediately cancel
        if self.read_only:
            event.cancel_tool = (
                f"Running in read-only mode. {reason}. "
                f"Mode transitions are disabled. Operation cancelled."
            )
            return

        # Otherwise, attempt transition
        allowed = self.mode_state.request_mode_transition(required_mode, reason)

        if not allowed:
            # Need user approval - raise interrupt
            response = event.interrupt(
                name=f"mode_transition_{required_mode.name}",
                reason={
                    "type": "mode_transition_required",
                    "current_mode": current_mode.name,
                    "required_mode": required_mode.name,
                    "tool_name": tool_name,
                    "risk_level": risk_level.name,
                    "message": reason
                }
            )

            # Process the user's response
            if response and response.get("approved") == True:
                self.mode_state.approve_transition(True)
                # Tool can now proceed
            else:
                # User rejected - cancel the tool call
                event.cancel_tool = (
                    f"Mode transition to {required_mode.name} was not approved. "
                    f"Staying in {current_mode.name} mode. Operation cancelled."
                )

    def on_invocation_end(self, event: AfterInvocationEvent) -> None:
        """Revert mode after the full agent invocation completes.

        Mode persists for the entire agent turn so multiple tool calls
        within the same invocation don't each trigger a new interrupt.
        """
        self.mode_state.revert_mode()


# Error messages
ERROR_MESSAGES = {
    "mode_transition_required": (
        "This operation requires {required_mode} mode, but you are currently "
        "in {current_mode} mode. Please approve the mode transition or cancel "
        "the operation."
    ),
    "mode_transition_rejected": (
        "Mode transition to {required_mode} was rejected. The operation has "
        "been cancelled. You remain in {current_mode} mode."
    ),
    "unknown_risk": (
        "Cannot determine risk level for tool '{tool_name}'. For safety, "
        "this operation requires EXECUTION mode."
    ),
    "read_only_mode": (
        "Running in read-only mode. Mode transitions are disabled. "
        "The operation has been cancelled."
    ),
}
