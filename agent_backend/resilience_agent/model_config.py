"""
Model configuration for all supported LLM providers.

Defines available models and default settings for:
- Anthropic (direct API)
- Amazon Bedrock (AWS-hosted models)
- Google Gemini
- OpenAI
"""

# Default model configurations for each provider
MODEL_CONFIGS = {
    "anthropic": {
        "models": [
            # Latest
            {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "max_tokens": 64000},
            {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "max_tokens": 128000},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "max_tokens": 64000},
            # Legacy
            {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5", "max_tokens": 64000},
            {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5", "max_tokens": 64000},
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "max_tokens": 64000},
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "max_tokens": 32000},
        ],
        "default_model": "claude-sonnet-4-6",
        "env_var": "ANTHROPIC_API_KEY"
    },
    "bedrock": {
        "models": [
            # Latest
            {"id": "anthropic.claude-sonnet-4-6-v1:0", "name": "Claude Sonnet 4.6 (Bedrock)", "max_tokens": 64000},
            {"id": "anthropic.claude-opus-4-6-v1:0", "name": "Claude Opus 4.6 (Bedrock)", "max_tokens": 128000},
            # Legacy
            {"id": "anthropic.claude-sonnet-4-5-20250929-v1:0", "name": "Claude Sonnet 4.5 (Bedrock)", "max_tokens": 64000},
            {"id": "anthropic.claude-sonnet-4-20250514-v1:0", "name": "Claude Sonnet 4 (Bedrock)", "max_tokens": 64000},
            {"id": "amazon.nova-premier-v1:0", "name": "Amazon Nova Premier", "max_tokens": 64000},
        ],
        "default_model": "anthropic.claude-sonnet-4-6-v1:0",
        "requires_aws": True
    },
    "gemini": {
        "models": [
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "max_tokens": 64000},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "max_tokens": 64000},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "max_tokens": 64000},
        ],
        "default_model": "gemini-2.5-flash",
        "env_var": "GOOGLE_API_KEY"
    },
    "openai": {
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o", "max_tokens": 16000},
            {"id": "gpt-4", "name": "GPT-4", "max_tokens": 8000},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "max_tokens": 4000},
        ],
        "default_model": "gpt-4o",
        "env_var": "OPENAI_API_KEY"
    }
}
