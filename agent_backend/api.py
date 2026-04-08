from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import boto3
from dotenv import load_dotenv
import os

from resilience_agent.agent import resilience_agent, mode_state, event_handler, model_state
from resilience_agent.model_factory import ModelFactory
from resilience_agent.model_config import MODEL_CONFIGS

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
# Use a mutable dict to store the current session so we can update it
aws_session_state = {
    "session": boto3.Session(),
    "sts": None
}
# Initialize STS client from the session
aws_session_state["sts"] = aws_session_state["session"].client('sts')


class ChatRequest(BaseModel):
    message: str
    sessionId: str


class InterruptResponse(BaseModel):
    interruptId: str
    approved: bool
    sessionId: str


class ProfileSwitchRequest(BaseModel):
    profile: str


class ModelSwitchRequest(BaseModel):
    provider: str
    model_id: str
    config: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    content: str
    events: Optional[List[Dict[str, Any]]] = None
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

        # Clear previous events before new agent call
        event_handler.clear()

        # Call the agent
        response = resilience_agent(request.message)

        # Get captured events
        events = event_handler.get_events()

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
                    events=events if events else None,
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

        return ChatResponse(
            content=content,
            events=events if events else None
        )

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
            # Clear previous events before resuming agent
            event_handler.clear()

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

            # Get captured events
            events = event_handler.get_events()

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
                        events=events if events else None,
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

            return ChatResponse(
                content=content,
                events=events if events else None
            )

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
        session = aws_session_state["session"]
        sts = aws_session_state["sts"]

        # Get AWS info
        aws_config = {
            "region": session.region_name,
            "profile": session.profile_name or "default",
            "accountId": sts.get_caller_identity().get('Account')
        }

        # Get model config
        model_config_dict = resilience_agent.model.get_config()
        model_config = {
            "provider": model_state["provider"],
            "modelId": model_config_dict.get('model_id', model_state["model_id"]),
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


@app.get("/api/profiles")
async def list_profiles():
    """
    List all available AWS profiles from ~/.aws/credentials and ~/.aws/config.
    """
    try:
        session = boto3.Session()
        available_profiles = session.available_profiles
        current_profile = aws_session_state["session"].profile_name or "default"

        return {
            "profiles": available_profiles,
            "current": current_profile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profiles/switch")
async def switch_profile(request: ProfileSwitchRequest):
    """
    Switch to a different AWS profile.
    """
    try:
        # Validate the profile exists
        available_profiles = boto3.Session().available_profiles
        if request.profile not in available_profiles:
            raise HTTPException(
                status_code=400,
                detail=f"Profile '{request.profile}' not found. Available profiles: {', '.join(available_profiles)}"
            )

        # Create new session with the requested profile
        new_session = boto3.Session(profile_name=request.profile)
        new_sts = new_session.client('sts')

        # Verify the profile works by making a test call
        try:
            account_id = new_sts.get_caller_identity().get('Account')
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to authenticate with profile '{request.profile}': {str(e)}"
            )

        # Update the global session state
        aws_session_state["session"] = new_session
        aws_session_state["sts"] = new_sts

        return {
            "success": True,
            "profile": request.profile,
            "region": new_session.region_name,
            "accountId": account_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/providers")
async def list_providers():
    """
    List all available LLM providers and their models.
    """
    try:
        return {
            "providers": MODEL_CONFIGS,
            "current": {
                "provider": model_state["provider"],
                "model_id": model_state["model_id"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/switch")
async def switch_model(request: ModelSwitchRequest):
    """
    Switch to a different model provider or model.
    """
    try:
        # Validate provider exists
        if request.provider not in MODEL_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{request.provider}' not found. Available providers: {', '.join(MODEL_CONFIGS.keys())}"
            )

        # Validate model_id exists for provider
        provider_config = MODEL_CONFIGS[request.provider]
        valid_model_ids = [m["id"] for m in provider_config["models"]]
        if request.model_id not in valid_model_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model_id}' not found for provider '{request.provider}'. Available models: {', '.join(valid_model_ids)}"
            )

        # Build configuration based on provider
        config = request.config or {}

        # Set model_id and default values
        config["model_id"] = request.model_id
        config.setdefault("temperature", 0.2)

        # Get max_tokens from model definition
        model_info = next((m for m in provider_config["models"] if m["id"] == request.model_id), None)
        if model_info:
            config.setdefault("max_tokens", model_info["max_tokens"])

        # Provider-specific configuration
        if request.provider == "anthropic":
            api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="ANTHROPIC_API_KEY not found in environment or config"
                )
            config["api_key"] = api_key

        elif request.provider == "bedrock":
            # Use current AWS session for Bedrock
            config["boto_session"] = aws_session_state["session"]
            config["region_name"] = aws_session_state["session"].region_name

        elif request.provider == "gemini":
            api_key = config.get("api_key") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="GOOGLE_API_KEY not found in environment or config"
                )
            config["api_key"] = api_key

        elif request.provider == "openai":
            api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="OPENAI_API_KEY not found in environment or config"
                )
            config["api_key"] = api_key

        # Create new model instance
        try:
            new_model = ModelFactory.create_model(request.provider, config)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create model: {str(e)}"
            )

        # Update the agent's model
        resilience_agent.model = new_model

        # Update model state
        model_state["provider"] = request.provider
        model_state["model_id"] = request.model_id
        model_state["config"] = config

        # Return updated model info
        model_config_dict = resilience_agent.model.get_config()
        return {
            "success": True,
            "provider": request.provider,
            "model_id": request.model_id,
            "modelId": model_config_dict.get('model_id', request.model_id),
            "maxTokens": model_config_dict.get('max_tokens', config.get("max_tokens")),
            "temperature": model_config_dict.get('params', {}).get('temperature', config.get("temperature")),
        }

    except HTTPException:
        raise
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
    uvicorn.run(app, host="0.0.0.0", port=8001)
