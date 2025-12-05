import boto3
from pprint import pprint
from strands import Agent
from strands_tools import use_aws
from strands.models.anthropic import AnthropicModel
from strands.handlers.callback_handler import PrintingCallbackHandler
from dotenv import load_dotenv 
import os

load_dotenv()

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

aws_agent = Agent(
    model=claude,
    name='AWS Agent',
    system_prompt='You are an AWS agent with access to AWS services for CRUD operations.',
    callback_handler=PrintingCallbackHandler(),
    tools=[use_aws]
)

if __name__ == "__main__":
    messages = []

    while True: 
        try: 
            user_input = input("\nUser: ")

            if user_input.lower() == 'exit':
                print("Goodbye!")
                break

            if not user_input:
                continue

            messages.append({
                "role": "user",
                "message": user_input
            })  

            response = aws_agent(user_input)    

            messages.append({
                "role": "assistant",
                "message": response
            })

        except Exception as e:
            print(f"Error: {e}")

