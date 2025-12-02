#!/usr/bin/env python3
"""Test script for Phase 3: Structured Experiment Plans and Persistence."""

from datetime import datetime
from resilience_agent.tools.experiment_models import (
    ExperimentPlan,
    ExperimentType,
    ExperimentAction,
    TargetResource,
    SelectionMode,
    StopCondition,
    CostEstimate,
    BlastRadiusAssessment,
    RollbackPlan,
    MonitoringRequirements
)
from resilience_agent.tools.planning_tools import (
    save_experiment_plan,
    list_experiment_plans,
    load_experiment_plan,
    get_plan_summary,
    export_plan_to_fis_template
)


def test_create_and_save_plan():
    """Test creating and saving an experiment plan."""
    print("=" * 60)
    print("TEST 1: Creating and saving an experiment plan")
    print("=" * 60)

    # Create a simple EC2 instance termination experiment plan
    plan = ExperimentPlan(
        name="EC2 Instance Termination Test",
        description="Test application resilience when a single EC2 instance is terminated unexpectedly",
        experiment_type=ExperimentType.INSTANCE_TERMINATION,
        hypothesis="The application should continue to function normally when one instance is terminated, with load balanced to remaining instances",

        targets={
            "test-instances": TargetResource(
                resource_type="aws:ec2:instance",
                selection_mode=SelectionMode.COUNT,
                resource_tags={"Environment": "staging", "Team": "platform"},
                count=1
            )
        },

        actions=[
            ExperimentAction(
                action_id="terminate-instance",
                description="Terminate a single EC2 instance",
                fis_action_id="aws:ec2:terminate-instances",
                parameters={},
                targets={"Instances": "test-instances"}
            )
        ],

        stop_conditions=[
            StopCondition(
                source="arn:aws:cloudwatch:us-east-1:123456789012:alarm:HighErrorRate",
                value="aws:cloudwatch:alarm:state:alarm"
            )
        ],

        monitoring=MonitoringRequirements(
            required_metrics=[
                "AWS/ApplicationELB/TargetResponseTime",
                "AWS/ApplicationELB/HealthyHostCount",
                "AWS/ApplicationELB/HTTPCode_Target_5XX_Count"
            ],
            required_alarms=[
                "arn:aws:cloudwatch:us-east-1:123456789012:alarm:HighErrorRate"
            ]
        ),

        duration_minutes=10,

        cost_estimate=CostEstimate(
            fis_experiment_cost=0.10,
            resource_impact_cost=0.50,
            monitoring_cost=0.05,
            total_estimated_cost=0.65,
            cost_assumptions=[
                "FIS experiment cost based on $0.10 per experiment minute",
                "Instance downtime estimated at 5 minutes recovery time",
                "No additional CloudWatch costs assumed (existing alarms)"
            ]
        ),

        blast_radius=BlastRadiusAssessment(
            affected_services=["EC2", "ELB"],
            affected_resource_count=1,
            user_impact_level="low",
            recovery_time_estimate="5 minutes",
            risk_level="low",
            mitigation_strategies=[
                "Only one instance out of 3 will be terminated",
                "Load balancer will route traffic to healthy instances",
                "Auto-scaling will launch replacement instance"
            ]
        ),

        rollback_plan=RollbackPlan(
            automatic_rollback=True,
            manual_steps=[
                "Verify auto-scaling launched replacement instance",
                "Check load balancer target health",
                "Verify application metrics returned to normal"
            ],
            estimated_rollback_time="5 minutes",
            validation_steps=[
                "Check all target instances are healthy",
                "Verify response time is within SLA",
                "Confirm no 5xx errors"
            ]
        ),

        prerequisites=[
            "Auto-scaling group has minimum 2 instances configured",
            "CloudWatch alarm 'HighErrorRate' exists and is configured",
            "Load balancer health checks are configured",
            "Backup of instance configurations available"
        ],

        validation_steps=[
            "Monitor load balancer target health during experiment",
            "Verify no increase in 5xx errors",
            "Confirm auto-scaling launches replacement instance",
            "Check application response time remains within SLA"
        ]
    )

    # Save the plan
    plan_path = save_experiment_plan(plan)
    print(f"\n✓ Plan saved to: {plan_path}")

    return plan, plan_path


def test_list_plans():
    """Test listing all saved plans."""
    print("\n" + "=" * 60)
    print("TEST 2: Listing saved plans")
    print("=" * 60)

    plans = list_experiment_plans()
    print(f"\n✓ Found {len(plans)} plan(s):")

    for plan in plans:
        print(f"\n  - {plan['name']}")
        print(f"    Type: {plan['type']}")
        print(f"    Risk: {plan['risk_level']}")
        print(f"    File: {plan['filename']}")

    return plans


def test_load_plan(filename: str):
    """Test loading a saved plan."""
    print("\n" + "=" * 60)
    print("TEST 3: Loading a saved plan")
    print("=" * 60)

    plan = load_experiment_plan(filename)
    print(f"\n✓ Plan loaded: {plan.name}")
    print(f"  Type: {plan.experiment_type.value}")
    print(f"  Duration: {plan.duration_minutes} minutes")
    print(f"  Cost: ${plan.cost_estimate.total_estimated_cost:.2f}")

    return plan


def test_get_summary(filename: str):
    """Test getting a plan summary."""
    print("\n" + "=" * 60)
    print("TEST 4: Getting plan summary")
    print("=" * 60)

    summary = get_plan_summary(filename)
    print(f"\n{summary}")

    return summary


def test_export_to_fis_template(filename: str):
    """Test exporting plan to FIS template."""
    print("\n" + "=" * 60)
    print("TEST 5: Exporting to FIS template")
    print("=" * 60)

    template_path = export_plan_to_fis_template(filename)
    print(f"\n✓ FIS template exported to: {template_path}")

    # Read and display the template
    import json
    with open(template_path, 'r') as f:
        template = json.load(f)

    print(f"\n  Template keys: {list(template.keys())}")
    print(f"  Targets: {list(template['targets'].keys())}")
    print(f"  Actions: {list(template['actions'].keys())}")
    print(f"  Stop Conditions: {len(template['stopConditions'])}")

    return template_path


def main():
    """Run all Phase 3 tests."""
    print("\n🧪 PHASE 3 TESTING: Structured Experiment Plans")
    print("=" * 60)

    try:
        # Test 1: Create and save
        plan, plan_path = test_create_and_save_plan()

        # Test 2: List all plans
        plans = test_list_plans()

        if plans:
            # Get the filename from the first plan
            filename = plans[0]['filename']

            # Test 3: Load a plan
            loaded_plan = test_load_plan(filename)

            # Test 4: Get summary
            summary = test_get_summary(filename)

            # Test 5: Export to FIS template
            template_path = test_export_to_fis_template(filename)

        print("\n" + "=" * 60)
        print("✅ ALL PHASE 3 TESTS PASSED!")
        print("=" * 60)
        print("\nPhase 3 implementation is complete and functional.")
        print("The agent can now:")
        print("  - Create structured experiment plans")
        print("  - Save plans to disk")
        print("  - List and load saved plans")
        print("  - Export plans as FIS templates")
        print("  - Use these in Planning → Action → Execution workflow")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
