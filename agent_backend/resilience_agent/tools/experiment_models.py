"""Pydantic models for structured experiment plans.

This module defines the data models for AWS FIS chaos engineering experiment plans,
including targets, actions, stop conditions, and complete experiment specifications.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ExperimentType(str, Enum):
    """Type of chaos engineering experiment."""
    NETWORK_LATENCY = "network_latency"
    NETWORK_PACKET_LOSS = "network_packet_loss"
    NETWORK_DISCONNECT = "network_disconnect"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_STRESS = "disk_stress"
    INSTANCE_TERMINATION = "instance_termination"
    INSTANCE_STOP = "instance_stop"
    INSTANCE_REBOOT = "instance_reboot"
    ECS_TASK_KILL = "ecs_task_kill"
    RDS_REBOOT = "rds_reboot"
    RDS_FAILOVER = "rds_failover"
    LAMBDA_THROTTLE = "lambda_throttle"
    CUSTOM = "custom"


class SelectionMode(str, Enum):
    """Resource selection mode for targeting."""
    ALL = "ALL"
    COUNT = "COUNT"
    PERCENT = "PERCENT"


class TargetResource(BaseModel):
    """AWS resource targeted by an experiment."""

    resource_type: str = Field(
        description="AWS resource type (e.g., aws:ec2:instance, aws:ecs:task)"
    )
    selection_mode: SelectionMode = Field(
        default=SelectionMode.ALL,
        description="How to select resources from the filter results"
    )
    resource_arns: Optional[List[str]] = Field(
        default=None,
        description="Specific resource ARNs to target (if known)"
    )
    resource_tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Tags for filtering resources (e.g., {'Environment': 'staging'})"
    )
    filters: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Advanced filters for resource selection"
    )
    count: Optional[int] = Field(
        default=None,
        description="Number of resources to target (for COUNT mode)"
    )
    percent: Optional[int] = Field(
        default=None,
        description="Percentage of resources to target (for PERCENT mode)",
        ge=1,
        le=100
    )

    @field_validator("percent")
    @classmethod
    def validate_percent(cls, v: Optional[int]) -> Optional[int]:
        """Ensure percent is between 1 and 100."""
        if v is not None and (v < 1 or v > 100):
            raise ValueError("Percent must be between 1 and 100")
        return v


class ExperimentAction(BaseModel):
    """Individual fault injection action in an experiment."""

    action_id: str = Field(
        description="Unique identifier for this action within the experiment"
    )
    description: str = Field(
        description="Human-readable description of what this action does"
    )
    fis_action_id: str = Field(
        description="AWS FIS action ID (e.g., aws:ec2:stop-instances)"
    )
    parameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Action-specific parameters (e.g., duration, magnitude)"
    )
    targets: Dict[str, str] = Field(
        description="Mapping of target name to target key in experiment template"
    )
    start_after: Optional[List[str]] = Field(
        default=None,
        description="List of action IDs that must complete before this action starts"
    )

    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, v: str) -> str:
        """Ensure action_id is valid (lowercase alphanumeric with hyphens)."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("action_id must be alphanumeric with hyphens or underscores")
        return v


class StopCondition(BaseModel):
    """Condition that automatically stops an experiment if triggered."""

    source: str = Field(
        description="CloudWatch alarm ARN that triggers the stop condition"
    )
    value: str = Field(
        default="aws:cloudwatch:alarm:state:alarm",
        description="State value that triggers the stop (default: alarm state)"
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Ensure source is a valid CloudWatch alarm ARN."""
        if not v.startswith("arn:aws:cloudwatch:"):
            raise ValueError("source must be a CloudWatch alarm ARN")
        return v


class CostEstimate(BaseModel):
    """Estimated cost breakdown for running the experiment."""

    fis_experiment_cost: float = Field(
        description="Cost of running the FIS experiment itself (typically minimal)"
    )
    resource_impact_cost: float = Field(
        description="Estimated cost from resource disruption (e.g., instance downtime)"
    )
    monitoring_cost: float = Field(
        default=0.0,
        description="Additional monitoring/observability costs"
    )
    total_estimated_cost: float = Field(
        description="Total estimated cost in USD"
    )
    cost_assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made in cost calculation"
    )


class BlastRadiusAssessment(BaseModel):
    """Assessment of experiment impact scope and risk."""

    affected_services: List[str] = Field(
        description="AWS services that will be affected"
    )
    affected_resource_count: int = Field(
        description="Number of resources that will be targeted"
    )
    user_impact_level: str = Field(
        description="Expected user impact: none, low, medium, high"
    )
    recovery_time_estimate: str = Field(
        description="Estimated time to recover (e.g., '5 minutes', '1 hour')"
    )
    risk_level: str = Field(
        description="Overall risk level: low, medium, high"
    )
    mitigation_strategies: List[str] = Field(
        default_factory=list,
        description="Strategies to mitigate risk"
    )


class RollbackPlan(BaseModel):
    """Plan for rolling back experiment effects."""

    automatic_rollback: bool = Field(
        description="Whether FIS will automatically rollback on stop"
    )
    manual_steps: List[str] = Field(
        default_factory=list,
        description="Manual steps required to restore service"
    )
    estimated_rollback_time: str = Field(
        description="Expected time to complete rollback"
    )
    validation_steps: List[str] = Field(
        default_factory=list,
        description="Steps to verify service is restored"
    )


class MonitoringRequirements(BaseModel):
    """Monitoring setup required for the experiment."""

    required_metrics: List[str] = Field(
        description="CloudWatch metrics that must be monitored"
    )
    required_alarms: List[str] = Field(
        description="CloudWatch alarms that should exist (ARNs or names)"
    )
    dashboard_url: Optional[str] = Field(
        default=None,
        description="URL to CloudWatch dashboard for monitoring"
    )
    log_groups: Optional[List[str]] = Field(
        default=None,
        description="CloudWatch Log Groups to monitor"
    )


class ExperimentPlan(BaseModel):
    """Complete structured plan for a chaos engineering experiment.

    This model represents the full specification of an FIS experiment,
    including all metadata, targets, actions, safety conditions, and
    operational details needed to execute the experiment safely.
    """

    # Core Metadata
    name: str = Field(
        description="Human-readable name for the experiment"
    )
    description: str = Field(
        description="Detailed description of the experiment's purpose and scope"
    )
    experiment_type: ExperimentType = Field(
        description="Type of chaos experiment being conducted"
    )
    hypothesis: str = Field(
        description="What you expect to learn or validate from this experiment"
    )

    # Targets and Actions
    targets: Dict[str, TargetResource] = Field(
        description="Named targets for the experiment (key: target name, value: target spec)"
    )
    actions: List[ExperimentAction] = Field(
        description="Ordered list of actions to execute"
    )

    # Safety and Monitoring
    stop_conditions: List[StopCondition] = Field(
        default_factory=list,
        description="Conditions that will automatically stop the experiment"
    )
    monitoring: MonitoringRequirements = Field(
        description="Required monitoring setup"
    )

    # Execution Details
    duration_minutes: int = Field(
        description="Expected duration of the experiment in minutes",
        ge=1
    )
    role_arn: Optional[str] = Field(
        default=None,
        description="IAM role ARN for FIS to assume when running the experiment"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Tags to apply to the experiment template"
    )

    # Risk Assessment
    cost_estimate: CostEstimate = Field(
        description="Estimated cost of running the experiment"
    )
    blast_radius: BlastRadiusAssessment = Field(
        description="Assessment of experiment impact and risk"
    )
    rollback_plan: RollbackPlan = Field(
        description="Plan for recovering from the experiment"
    )

    # Prerequisites and Validation
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Conditions that must be met before running (e.g., backups, approvals)"
    )
    validation_steps: List[str] = Field(
        default_factory=list,
        description="Steps to validate the experiment worked as expected"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this plan was created"
    )
    created_by: str = Field(
        default="resilience_architect",
        description="Who or what created this plan"
    )
    version: str = Field(
        default="1.0",
        description="Plan version for tracking changes"
    )

    def to_fis_template(self) -> Dict[str, Any]:
        """Convert this plan to an AWS FIS experiment template.

        Returns:
            Dictionary suitable for use with fis:create_experiment_template
        """
        # Build targets section
        fis_targets = {}
        for target_name, target_spec in self.targets.items():
            fis_target = {
                "resourceType": target_spec.resource_type,
                "selectionMode": target_spec.selection_mode.value,
            }

            # Add resource ARNs if specified
            if target_spec.resource_arns:
                fis_target["resourceArns"] = target_spec.resource_arns

            # Add resource tags if specified
            if target_spec.resource_tags:
                fis_target["resourceTags"] = target_spec.resource_tags

            # Add filters if specified
            if target_spec.filters:
                fis_target["filters"] = target_spec.filters

            # Add parameters based on selection mode
            if target_spec.selection_mode == SelectionMode.COUNT and target_spec.count:
                fis_target["parameters"] = {"count": str(target_spec.count)}
            elif target_spec.selection_mode == SelectionMode.PERCENT and target_spec.percent:
                fis_target["parameters"] = {"percentage": str(target_spec.percent)}

            fis_targets[target_name] = fis_target

        # Build actions section
        fis_actions = {}
        for action in self.actions:
            fis_action = {
                "actionId": action.fis_action_id,
                "description": action.description,
                "parameters": action.parameters,
                "targets": action.targets,
            }

            if action.start_after:
                fis_action["startAfter"] = action.start_after

            fis_actions[action.action_id] = fis_action

        # Build stop conditions section
        fis_stop_conditions = []
        for stop_condition in self.stop_conditions:
            fis_stop_conditions.append({
                "source": stop_condition.source,
                "value": stop_condition.value,
            })

        # Build complete template
        template = {
            "description": self.description,
            "targets": fis_targets,
            "actions": fis_actions,
            "stopConditions": fis_stop_conditions,
            "tags": {
                **self.tags,
                "Name": self.name,
                "ExperimentType": self.experiment_type.value,
                "CreatedBy": self.created_by,
                "Version": self.version,
            }
        }

        # Add role ARN if specified
        if self.role_arn:
            template["roleArn"] = self.role_arn

        return template

    def get_summary(self) -> str:
        """Get a human-readable summary of the experiment plan."""
        summary_lines = [
            f"Experiment Plan: {self.name}",
            f"Type: {self.experiment_type.value}",
            f"Risk Level: {self.blast_radius.risk_level}",
            f"Duration: {self.duration_minutes} minutes",
            f"Estimated Cost: ${self.cost_estimate.total_estimated_cost:.2f}",
            f"",
            f"Hypothesis: {self.hypothesis}",
            f"",
            f"Targets: {len(self.targets)} target(s)",
            f"Actions: {len(self.actions)} action(s)",
            f"Stop Conditions: {len(self.stop_conditions)} condition(s)",
            f"",
            f"Blast Radius:",
            f"  - Affected Services: {', '.join(self.blast_radius.affected_services)}",
            f"  - Resource Count: {self.blast_radius.affected_resource_count}",
            f"  - User Impact: {self.blast_radius.user_impact_level}",
            f"  - Recovery Time: {self.blast_radius.recovery_time_estimate}",
        ]

        if self.prerequisites:
            summary_lines.append(f"\nPrerequisites ({len(self.prerequisites)}):")
            for prereq in self.prerequisites:
                summary_lines.append(f"  - {prereq}")

        return "\n".join(summary_lines)

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
