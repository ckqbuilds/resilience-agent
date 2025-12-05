"""AWS Knowledge Agent for documentation and best practices.

Provides access to AWS documentation, knowledge base retrieval,
and best practices for resilience engineering and FIS experiments.
"""

from typing import Any
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.sse import sse_client
from mcp import stdio_client, StdioServerParameters
from strands.models.anthropic import AnthropicModel
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.tools import tool
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import logging

# Add parent directory to path for direct execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

logger = logging.getLogger(__name__)

# aws_knowledge_mcp = MCPClient(lambda: sse_client("https://knowledge-mcp.global.api.aws"))

aws_documentation_mcp = MCPClient(lambda: stdio_client(
StdioServerParameters(
    command="uvx",
    args=["awslabs.aws-documentation-mcp-server@latest"]
)
))

aws_knowledge_mcp = MCPClient(lambda: stdio_client(
StdioServerParameters(
    command="uvx",
    args=["https://knowledge-mcp.global.api.aws"],
    env={
        "type": "http"
    }
)
))

# Bedrock Knowledge Base for custom knowledge retrieval
bedrock_kb_mcp = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
            env={
                "AWS_PROFILE": "default",
                "AWS_REGION": "us-east-1",
                "FASTMCP_LOG_LEVEL": "ERROR",
                "KB_INCLUSION_TAG_KEY": "optional-tag-key-to-filter-kbs",
                "BEDROCK_KB_RERANKING_ENABLED": "false"
            }
        )
    )
)


claude = AnthropicModel(
    client_args={
        'api_key': os.getenv("ANTHROPIC_API_KEY")
    },
    model_id='claude-haiku-4-5',
    max_tokens=64000,
    params={
        "temperature": 0.2
    }
)

@tool
def aws_knowledge_agent(query: str):

    try: 
        knowledge_agent = Agent(
            name="AWS Knowledge Agent",
            description="Provides AWS documentation, best practices, and knowledge base access for resilience engineering.",
            system_prompt="""You are the AWS Knowledge Agent, an expert in AWS services, architectures, and best practices.
                            Your role is to:

                            1. Provide AWS documentation and service guidance
                            2. Recommend resilience engineering best practices
                            3. Share FIS experiment design patterns
                            4. Help architect resilient and fault-tolerant systems
                            5. Retrieve and explain AWS knowledge base information
                            6. Provide solution recommendations based on requirements

                            Always prioritize best practices and share lessons learned from successful deployments.
                            Help other agents understand AWS services and capabilities.
                            Provide clear, actionable recommendations for resilience improvements.""",
            model=claude,
            tools=[aws_documentation_mcp, bedrock_kb_mcp],
            load_tools_from_directory=False,
            callback_handler=PrintingCallbackHandler(),
        )

        response = knowledge_agent(query)
        return response
    
    except Exception as e:
        print(f"Invocation error: {e}")


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

        response = aws_knowledge_agent(user_input)
        

        messages.append({"role": "assistant", "message": response})
        print("\n")
        

        # print(f"\nAssistant: {response.message['content']}")
        print("\n")
        # pprint(response.metrics.get_summary()['accumulated_usage'])
