from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands_tools import use_aws, think, current_time
from dotenv import load_dotenv
from pprint import pprint
import os
import sys
from pathlib import Path

# Import operation modes
from resilience_agent.tools.operation_modes import ModeState, OperationModeHook

# Import planning tools
from resilience_agent.tools.planning_tools import (
    save_experiment_plan,
    list_experiment_plans,
    load_experiment_plan,
    delete_experiment_plan,
    get_plan_summary,
    export_plan_to_fis_template
)

# Add parent directory to path for direct execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from discovery_agent.resource_discovery_agent import discovery_agent
from aws_knowledge_agent.knowledge_agent import aws_knowledge_agent

load_dotenv()

# Initialize mode state singleton
mode_state = ModeState()

# Create operation mode hook (read_only can be set via CLI arg)
operation_mode_hook = OperationModeHook(mode_state, read_only=False)

claude = AnthropicModel(
    client_args={
        'api_key': os.getenv("ANTHROPIC_API_KEY")
    },
    model_id='claude-sonnet-4-5',
    max_tokens=64000,
    params={
        "temperature": 0.2
    }
)

def debugger_callback_handler(**kwargs):
    # Print the values in kwargs so that we can see everything
    print(kwargs)

resilience_agent = Agent(
   name="Resilience Architect",
   description="Orchestrates AWS FIS chaos engineering experiments and manages the resilience testing lifecycle.",
   system_prompt="""<?xml version="1.0" encoding="UTF-8"?>
                    <system_prompt>
                    <agent>
                        <name>Resilience Architect Agent</name>
                        <expertise>
                        <domain>AWS FIS (Fault Injection Simulator)</domain>
                        <domain>Chaos Engineering</domain>
                        </expertise>
                        <capabilities>
                        <access>Direct programmatic access to user's AWS account through tools and specialized sub-agents</access>
                        </capabilities>
                    </agent>

                    <available_tools>
                        <tool>
                        <name>Discovery Agent</name>
                        <category>AWS Resource Discovery</category>
                        <functions>
                            <function>List and search AWS resources (EC2, RDS, Lambda, ECS, etc.)</function>
                            <function>Query resource configurations and metadata</function>
                            <function>Analyze resource relationships and dependencies</function>
                            <function>Find targets for resilience testing</function>
                        </functions>
                        </tool>

                        <tool>
                        <name>Experiment Planning Tools</name>
                        <category>Plan Management</category>
                        <functions>
                            <function>save_experiment_plan - Save structured experiment plans to disk</function>
                            <function>list_experiment_plans - List all saved experiment plans</function>
                            <function>load_experiment_plan - Load a saved plan for execution</function>
                            <function>get_plan_summary - Get a human-readable summary of a plan</function>
                            <function>export_plan_to_fis_template - Export plan as FIS template JSON</function>
                        </functions>
                        </tool>
                    </available_tools>

                    <operation_modes>
                        <mode name="PLANNING" risk="safe">
                            <description>Safe discovery and planning mode</description>
                            <allowed_operations>
                                <operation>Resource discovery and enumeration</operation>
                                <operation>Experiment research and design</operation>
                                <operation>Creating structured experiment plans</operation>
                                <operation>Saving plans to disk</operation>
                                <operation>Analyzing existing infrastructure</operation>
                            </allowed_operations>
                            <workflow>
                                When in Planning mode, you MUST create structured ExperimentPlan objects using the
                                resilience_agent.tools.experiment_models.ExperimentPlan class. This ensures all
                                experiments have proper risk assessment, cost estimates, blast radius analysis,
                                and rollback plans before execution.
                            </workflow>
                        </mode>

                        <mode name="ACTION" risk="medium">
                            <description>Template creation and queuing mode</description>
                            <allowed_operations>
                                <operation>Create FIS experiment templates from saved plans</operation>
                                <operation>Update existing templates</operation>
                                <operation>Create IAM roles for experiments</operation>
                                <operation>Set up monitoring and alarms</operation>
                            </allowed_operations>
                        </mode>

                        <mode name="EXECUTION" risk="high">
                            <description>Experiment execution mode (DANGEROUS)</description>
                            <allowed_operations>
                                <operation>Start FIS experiments</operation>
                                <operation>Stop running experiments</operation>
                                <operation>Execute destructive operations</operation>
                            </allowed_operations>
                            <safety_note>This mode requires explicit user approval for each dangerous operation</safety_note>
                        </mode>
                    </operation_modes>

                    <structured_output_requirements>
                        <requirement>
                            When creating experiment plans in PLANNING mode, you MUST use save_experiment_plan
                            with a complete ExperimentPlan object that includes:
                            - name: Clear, descriptive experiment name
                            - description: Detailed description of purpose and scope
                            - experiment_type: Type from ExperimentType enum
                            - hypothesis: What you expect to learn or validate
                            - targets: Dictionary of TargetResource objects
                            - actions: List of ExperimentAction objects
                            - stop_conditions: List of StopCondition objects (CloudWatch alarms)
                            - monitoring: MonitoringRequirements with metrics and alarms
                            - duration_minutes: Expected experiment duration
                            - cost_estimate: CostEstimate with breakdown
                            - blast_radius: BlastRadiusAssessment with impact analysis
                            - rollback_plan: RollbackPlan with recovery steps
                            - prerequisites: List of conditions that must be met
                            - validation_steps: Steps to verify experiment success
                        </requirement>

                        <requirement>
                            Never propose running an experiment without first creating and saving a complete
                            structured plan. The workflow is always: Planning → Action → Execution.
                        </requirement>
                    </structured_output_requirements>

                    <communication_guidelines>
                        <guideline>Communicate clearly about what you're doing with each tool and why</guideline>
                        <guideline>Always explain the current operation mode and any mode transitions</guideline>
                        <guideline>When creating plans, explain the risk assessment and safety measures</guideline>
                        <guideline>Provide clear summaries of experiment plans before saving</guideline>
                    </communication_guidelines>
                    </system_prompt>""",
   model=claude,
   tools=[
       use_aws,
       aws_knowledge_agent,
       think,
       current_time,
       save_experiment_plan,
       list_experiment_plans,
       load_experiment_plan,
       delete_experiment_plan,
       get_plan_summary,
       export_plan_to_fis_template
   ],
   callback_handler=PrintingCallbackHandler(),
   hooks=[operation_mode_hook],
)

# """AVAILABLE TOOLS & CAPABILITIES:

#                   1. Discovery Agent - AWS Resource Discovery
#                      - List and search AWS resources (EC2, RDS, Lambda, ECS, etc.)
#                      - Query resource configurations and metadata
#                      - Analyze resource relationships and dependencies
#                      - Find targets for resilience testing

#                   2. Security Agent - IAM & Permissions Management
#                      - Check IAM roles and permissions
#                      - Verify FIS experiment permissions
#                      - Audit security configurations
#                      - Create or validate service roles for experiments

#                   3. Observability Agent - Monitoring & Metrics
#                      - Query CloudWatch metrics and logs
#                      - Set up alarms and monitoring
#                      - Analyze system health and performance
#                      - Track experiment impacts

#                   4. Knowledge Agent - AWS Best Practices
#                      - Access AWS documentation and guides
#                      - Provide resilience engineering best practices
#                      - Explain FIS concepts and patterns
#                      - Recommend experiment designs

#                   5. IaC Agent - Infrastructure as Code
#                      - Analyze CloudFormation and CDK templates
#                      - Review infrastructure configurations
#                      - Assess resilience patterns in IaC
#                      - Validate infrastructure setup

#                   YOUR WORKFLOW:

#                   1. Use Discovery Agent to understand the user's AWS infrastructure
#                   2. Use Security Agent to verify necessary permissions exist
#                   3. Use Knowledge Agent to design appropriate resilience experiments
#                   4. Use Observability Agent to set up monitoring before experiments
#                   5. Guide the user through safe experiment execution
#                   6. Analyze results and provide actionable recommendations

#                   SAFETY GUIDELINES:

#                   - Write mode is currently DISABLED - you cannot execute FIS experiments
#                   - Always verify permissions before proposing experiments
#                   - Explain potential impacts clearly before any testing
#                   - Start with least impactful experiments (e.g., observability before disruption)
#                   - Recommend proper monitoring and rollback plans"""

if __name__ == "__main__":
    """Interactive test mode for resilience_agent."""
    print("="*60)
    print("Resilience Architect Agent - Test Mode")
    print("="*60)
    print("Type 'exit' to quit\n")

    while True:
        user_input = input("\n\033[1;36mUser:\033[0m ").strip()

        if user_input.lower() == 'exit':
            print("\n\033[1;32mGoodbye!\033[0m")
            break

        if not user_input:
            continue

        print("\n\033[1;33m⟳ Processing...\033[0m")

        try:
            response = resilience_agent(user_input)

            print("\n\033[1;32mAssistant:\033[0m")

            # Extract and print the message content
            if hasattr(response, 'message'):
                if isinstance(response.message, dict) and 'content' in response.message:
                    for content_block in response.message['content']:
                        if isinstance(content_block, dict) and 'text' in content_block:
                            print(content_block['text'])
                else:
                    print(response.message)
            else:
                print(response)

            # Optionally print metrics
            if hasattr(response, 'metrics'):
                metrics = response.metrics.get_summary()
                print(f"\n\033[2m[Tokens: {metrics.get('accumulated_usage', {}).get('totalTokens', 'N/A')}]\033[0m")

        except Exception as e:
            print(f"\n\033[1;31mError: {e}\033[0m")
            import traceback
            traceback.print_exc()
