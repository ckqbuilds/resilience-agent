from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import boto3
from dotenv import load_dotenv
import os

from resilience_agent.agent import resilience_agent, mode_state

load_dotenv()

app = FastAPI(title="Resilience Architect API")

# Add CORS middleware to allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active sessions
sessions: Dict[str, Any] = {}

# Initialize AWS clients for info endpoint
sts = boto3.client('sts')
session = boto3.Session()


class ChatRequest(BaseModel):
    message: str
    sessionId: str


class InterruptResponse(BaseModel):
    interruptId: str
    approved: bool
    sessionId: str


class ChatResponse(BaseModel):
    content: str
    interrupt: Optional[Dict[str, Any]] = None


@app.get("/")
async def root():
    return {"message": "Resilience Architect API", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the resilience agent and get a response.
    """
    try:
        # Get or create session
        if request.sessionId not in sessions:
            sessions[request.sessionId] = {
                "messages": [],
                "pending_interrupt": None,
                "conversation_history": []
            }

        session_data = sessions[request.sessionId]

        # Check if there's a pending interrupt that needs to be resolved first
        if session_data.get("pending_interrupt"):
            raise HTTPException(
                status_code=409,
                detail="Cannot send new message while mode transition is pending. Please approve or reject the mode transition first."
            )

        # Store user message in history
        session_data["conversation_history"].append(request.message)

        # Call the agent
        response = resilience_agent(request.message)

        # Check if there's an interrupt (mode transition request)
        if hasattr(response, 'stop_reason') and hasattr(response, 'interrupts') and response.interrupts:
            # Handle interrupt
            interrupt = response.interrupts[0]
            reason_data = interrupt.reason

            if reason_data.get("type") == "mode_transition_required":
                # Store interrupt in session with the response object
                session_data["pending_interrupt"] = {
                    "id": interrupt.id,
                    "response_obj": response,
                    "original_message": request.message
                }

                # Return interrupt info to frontend
                return ChatResponse(
                    content="",
                    interrupt={
                        "id": interrupt.id,
                        "currentMode": reason_data["current_mode"],
                        "requiredMode": reason_data["required_mode"],
                        "toolName": reason_data["tool_name"],
                        "reason": reason_data["message"],
                        "color": "yellow",
                        "description": f"Transitioning from {reason_data['current_mode']} to {reason_data['required_mode']}"
                    }
                )

        # Extract text from normal response
        content = extract_text_from_response(response)

        return ChatResponse(content=content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interrupt", response_model=ChatResponse)
async def respond_to_interrupt(request: InterruptResponse):
    """
    Respond to a mode transition interrupt with approval/rejection.
    """
    try:
        session_data = sessions.get(request.sessionId)

        # Validate session exists
        if not session_data:
            raise HTTPException(status_code=400, detail=f"Session {request.sessionId} not found")

        # Validate pending interrupt exists
        if not session_data.get("pending_interrupt"):
            raise HTTPException(
                status_code=400,
                detail="No pending interrupt found. The interrupt may have already been processed or expired."
            )

        pending = session_data["pending_interrupt"]

        # Validate interrupt ID matches
        if pending["id"] != request.interruptId:
            raise HTTPException(
                status_code=400,
                detail=f"Interrupt ID mismatch. Expected {pending['id']}, got {request.interruptId}"
            )

        try:
            # Create interrupt response in the format the agent expects
            interrupt_response = {
                "interruptResponse": {
                    "interruptId": request.interruptId,
                    "response": {"approved": request.approved}
                }
            }

            # Resume agent with the interrupt response
            # The agent expects a list of responses when resuming from interrupt
            result = resilience_agent([interrupt_response])

            # Clear pending interrupt after successful resumption
            session_data["pending_interrupt"] = None

            # Check if the resumed execution also has interrupts
            if hasattr(result, 'stop_reason') and hasattr(result, 'interrupts') and result.interrupts:
                interrupt = result.interrupts[0]
                reason_data = interrupt.reason

                if reason_data.get("type") == "mode_transition_required":
                    # Store new interrupt
                    session_data["pending_interrupt"] = {
                        "id": interrupt.id,
                        "response_obj": result
                    }

                    return ChatResponse(
                        content="",
                        interrupt={
                            "id": interrupt.id,
                            "currentMode": reason_data["current_mode"],
                            "requiredMode": reason_data["required_mode"],
                            "toolName": reason_data["tool_name"],
                            "reason": reason_data["message"],
                            "color": "yellow",
                            "description": f"Transitioning from {reason_data['current_mode']} to {reason_data['required_mode']}"
                        }
                    )

            # Extract text from response
            content = extract_text_from_response(result)

            return ChatResponse(content=content)

        except Exception as agent_error:
            # Don't clear the interrupt if the agent failed
            raise HTTPException(
                status_code=500,
                detail=f"Agent error during interrupt response: {str(agent_error)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/info")
async def get_info():
    """
    Get LLM, AWS, and session information.
    """
    try:
        # Get AWS info
        aws_config = {
            "region": session.region_name,
            "profile": session.profile_name or "default",
            "accountId": sts.get_caller_identity().get('Account')
        }

        # Get model config
        model_config_dict = resilience_agent.model.get_config()
        model_config = {
            "modelId": model_config_dict.get('model_id', 'claude-sonnet-4-5'),
            "maxTokens": model_config_dict.get('max_tokens', 64000),
            "temperature": model_config_dict.get('params', {}).get('temperature', 0.2),
            "tools": resilience_agent.tool_names
        }

        # Get session stats (dummy data for now)
        session_stats = {
            "totalRequests": 0,
            "avgResponseTime": "0.0s",
            "totalCost": "$0.00",
            "sessionDuration": "00:00:00",
            "tokensUsed": 0,
            "tokensTotal": 200000
        }

        return {
            "aws": aws_config,
            "model": model_config,
            "stats": session_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_text_from_response(response) -> str:
    """
    Extract text content from agent response.
    """
    try:
        if hasattr(response, 'message'):
            if isinstance(response.message, dict) and 'content' in response.message:
                text_parts = []
                for content_block in response.message['content']:
                    if isinstance(content_block, dict) and 'text' in content_block:
                        text_parts.append(content_block['text'])
                return '\n'.join(text_parts) if text_parts else str(response.message)
            else:
                return str(response.message)
        else:
            return str(response)
    except (KeyError, IndexError, TypeError):
        return str(response)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
