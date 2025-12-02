"""Resource Discovery Agent implementation.

Specializes in discovering and analyzing AWS resources within accounts,
using AWS Resource Explorer and Config to map infrastructure and relationships.
"""

from typing import Any
from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.tools import tool
import logging
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
# from strands.models.ollama import OllamaModel

# Add parent directory to path for direct execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from discovery_agent.tools.resource_explorer import list_views, search_resources, create_view, discover_relationships
except ImportError:
    from tools.resource_explorer import list_views, search_resources, create_view, discover_relationships

load_dotenv()

logger = logging.getLogger(__name__)


claude = AnthropicModel(
    client_args={
        'api_key': os.getenv("ANTHROPIC_API_KEY")
    },
    model_id='claude-haiku-4-5',
    max_tokens=30000,
    params={
        "temperature": 0.2
    }
)

# ollama = OllamaModel(
#     host="http://localhost:11434",
#     model_id="qwen3:0.6b"
# )


@tool
def discovery_agent(query: str):
    """Create and return the Resource Discovery Agent.

    Args:
        model: LLM model instance (created by ModelFactory from config)

    Returns:
        Configured Discovery Agent ready to use

    The Discovery Agent specializes in:
    - Finding AWS resources across accounts and regions
    - Analyzing resource relationships and dependencies
    - Providing structured resource inventory
    - Identifying candidate resources for resilience testing
    """
    
    try:

        discovery_agent = Agent(
            name="Resource Discovery Agent",
            description="Discovers and analyzes AWS resources to map infrastructure and identify testing targets.",
            system_prompt="""<system_prompt>
                            <agent>
                                <name>Resource Discovery Agent</name>
                                <expertise>Exploring and cataloging AWS infrastructure</expertise>
                            </agent>

                            <role>
                                <responsibility>Discover AWS resources using Resource Explorer and AWS Config</responsibility>
                                <responsibility>Analyze resource relationships and dependencies</responsibility>
                                <responsibility>Identify resources suitable for resilience testing</responsibility>
                                <responsibility>Provide clear, structured information about discovered resources</responsibility>
                                <responsibility>Help users understand their infrastructure landscape</responsibility>
                            </role>

                            <operational_guidelines>
                                <guideline>
                                <name>Regional and Account Respect</name>
                                <description>Respect the configured AWS region and account</description>
                                </guideline>
                                <guideline>
                                <name>Structured Output</name>
                                <description>Provide structured output with resource details</description>
                                </guideline>
                                <guideline>
                                <name>Relationship Analysis</name>
                                <description>Identify relationships between resources (e.g., ASG → EC2 → Security Groups)</description>
                                </guideline>
                                <guideline>
                                <name>Impact Assessment</name>
                                <description>Flag resources that might impact other systems if disrupted</description>
                                </guideline>
                                <guideline>
                                <name>Chaos Experiment Recommendations</name>
                                <description>Suggest resources that would be good candidates for chaos experiments</description>
                                </guideline>
                            </operational_guidelines>

                            <discovery_principles>
                                <principle>Always respect configured AWS region and account boundaries</principle>
                                <principle>Deliver information in structured, clearly organized formats</principle>
                                <principle>Map dependencies and relationships across resource tiers</principle>
                                <principle>Assess blast radius and downstream impact of each resource</principle>
                                <principle>Recommend high-value targets for resilience testing</principle>
                            </discovery_principles>
                            </system_prompt>""",
            model=claude,
            tools=[list_views, search_resources, create_view, discover_relationships],
            load_tools_from_directory=True,
            callback_handler=None,
        )

        response = discovery_agent(query)

        return response

        # messages = []
        # while True:
        #     try:
                

        #         user_input = query

        #         messages.append({
        #             "role": "user",
        #             "message": user_input
        #         })

        #         response = discovery_agent(user_input)

        #         messages.append({
        #             "role": "assistant",
        #             "message": response
        #         })

        #         return response
            
            
        #     except Exception as e:
        #         print(f"Error message: {e}")
    
    except Exception as e:
        return f"Error processing request: {e}"


if __name__ == "__main__":
    messages = []

    while True:
        user_input = input("\nUser: ").strip()

        if user_input.lower() == 'exit':
            print("Goodbye")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        print("\n")

        response = discovery_agent(user_input)

        messages.append({"role": "assistant", "message": response})

        # print(f"\nAssistant: {response.message['content']}")
        print("\n")
        # pprint(response.metrics.get_summary()['accumulated_usage'])