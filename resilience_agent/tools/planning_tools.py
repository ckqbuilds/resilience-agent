"""Tools for saving, loading, and managing experiment plans.

This module provides tools for persisting structured experiment plans to disk,
enabling the Planning → Action workflow where plans are created in Planning mode
and later loaded in Action mode for execution.
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from strands import tool
from resilience_agent.tools.experiment_models import ExperimentPlan


# Directory for storing experiment plans
PLANS_DIR = Path.home() / ".experiment_plans"


def ensure_plans_directory() -> Path:
    """Ensure the experiment plans directory exists.

    Returns:
        Path to the plans directory
    """
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    return PLANS_DIR


@tool
def save_experiment_plan(plan: ExperimentPlan, filename: Optional[str] = None) -> str:
    """Save an experiment plan to disk.

    This tool allows the agent to persist structured experiment plans during
    Planning mode, which can later be loaded and executed in Action/Execution modes.

    Args:
        plan: The ExperimentPlan object to save
        filename: Optional filename (without extension). If not provided,
                 generates a filename from the plan name and timestamp

    Returns:
        Full path to the saved plan file

    Example:
        >>> plan = ExperimentPlan(
        ...     name="EC2 Instance Termination Test",
        ...     description="Test instance recovery",
        ...     # ... other fields ...
        ... )
        >>> path = save_experiment_plan(plan)
        >>> print(f"Plan saved to: {path}")
    """
    ensure_plans_directory()

    # Generate filename if not provided
    if filename is None:
        # Sanitize plan name for filename
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in plan.name.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}"

    # Ensure .json extension
    if not filename.endswith(".json"):
        filename = f"{filename}.json"

    # Full path
    file_path = PLANS_DIR / filename

    # Convert plan to JSON
    plan_dict = plan.model_dump(mode="json")

    # Write to file with pretty formatting
    with open(file_path, "w") as f:
        json.dump(plan_dict, f, indent=2, default=str)

    return str(file_path)


@tool
def list_experiment_plans() -> List[Dict[str, Any]]:
    """List all saved experiment plans.

    Returns:
        List of dictionaries with plan metadata:
        - filename: Name of the plan file
        - name: Experiment name
        - type: Experiment type
        - risk_level: Risk assessment
        - created_at: Creation timestamp
        - file_path: Full path to the file

    Example:
        >>> plans = list_experiment_plans()
        >>> for plan in plans:
        ...     print(f"{plan['name']} - Risk: {plan['risk_level']}")
    """
    ensure_plans_directory()

    plans = []

    # Iterate over all .json files in the plans directory
    for file_path in PLANS_DIR.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                plan_data = json.load(f)

            # Extract key metadata
            metadata = {
                "filename": file_path.name,
                "name": plan_data.get("name", "Unknown"),
                "type": plan_data.get("experiment_type", "Unknown"),
                "risk_level": plan_data.get("blast_radius", {}).get("risk_level", "Unknown"),
                "created_at": plan_data.get("created_at", "Unknown"),
                "file_path": str(file_path),
            }

            plans.append(metadata)

        except (json.JSONDecodeError, KeyError) as e:
            # Skip invalid plan files
            print(f"Warning: Could not load plan from {file_path}: {e}")
            continue

    # Sort by creation time (newest first)
    plans.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    return plans


@tool
def load_experiment_plan(filename: str) -> ExperimentPlan:
    """Load an experiment plan from disk.

    Args:
        filename: Name of the plan file (with or without .json extension)
                 or full path to the plan file

    Returns:
        ExperimentPlan object loaded from the file

    Raises:
        FileNotFoundError: If the plan file doesn't exist
        ValueError: If the plan file is invalid or cannot be parsed

    Example:
        >>> plan = load_experiment_plan("ec2_instance_termination_test_20240101_120000.json")
        >>> print(plan.name)
        EC2 Instance Termination Test
    """
    # Handle full paths
    if os.path.isabs(filename):
        file_path = Path(filename)
    else:
        ensure_plans_directory()

        # Ensure .json extension
        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        file_path = PLANS_DIR / filename

    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"Plan file not found: {file_path}")

    # Load and parse the JSON
    try:
        with open(file_path, "r") as f:
            plan_data = json.load(f)

        # Create ExperimentPlan from the data
        plan = ExperimentPlan(**plan_data)
        return plan

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in plan file {file_path}: {e}")
    except Exception as e:
        raise ValueError(f"Could not load plan from {file_path}: {e}")


@tool
def delete_experiment_plan(filename: str) -> bool:
    """Delete an experiment plan file.

    Args:
        filename: Name of the plan file (with or without .json extension)
                 or full path to the plan file

    Returns:
        True if the file was deleted, False if it didn't exist

    Example:
        >>> deleted = delete_experiment_plan("old_plan.json")
        >>> if deleted:
        ...     print("Plan deleted successfully")
    """
    # Handle full paths
    if os.path.isabs(filename):
        file_path = Path(filename)
    else:
        ensure_plans_directory()

        # Ensure .json extension
        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        file_path = PLANS_DIR / filename

    # Check if file exists
    if not file_path.exists():
        return False

    # Delete the file
    file_path.unlink()
    return True


@tool
def get_plan_summary(filename: str) -> str:
    """Get a human-readable summary of a saved plan without fully loading it.

    Args:
        filename: Name of the plan file (with or without .json extension)

    Returns:
        Formatted summary string

    Example:
        >>> summary = get_plan_summary("my_experiment.json")
        >>> print(summary)
    """
    plan = load_experiment_plan(filename)
    return plan.get_summary()


@tool
def export_plan_to_fis_template(filename: str, output_path: Optional[str] = None) -> str:
    """Export a plan as a FIS experiment template JSON file.

    This is useful for manual review or direct use with AWS CLI/Console.

    Args:
        filename: Name of the plan file
        output_path: Optional output path for the template. If not provided,
                    saves next to the plan file with _template.json suffix

    Returns:
        Path to the exported template file

    Example:
        >>> template_path = export_plan_to_fis_template("my_plan.json")
        >>> print(f"FIS template saved to: {template_path}")
    """
    plan = load_experiment_plan(filename)

    # Generate output path if not provided
    if output_path is None:
        plan_path = Path(filename) if os.path.isabs(filename) else PLANS_DIR / filename
        output_path = plan_path.with_name(plan_path.stem + "_template.json")
    else:
        output_path = Path(output_path)

    # Convert to FIS template
    template = plan.to_fis_template()

    # Write to file
    with open(output_path, "w") as f:
        json.dump(template, f, indent=2)

    return str(output_path)
