"""
Model factory for creating LLM instances across different providers.

Supports:
- Anthropic (direct API)
- Amazon Bedrock
- Google Gemini
- OpenAI
"""

from typing import Dict, Any, Optional
from strands.models.anthropic import AnthropicModel
from strands.models import BedrockModel
from strands.models.gemini import GeminiModel
from strands.models.openai import OpenAIModel


class ModelFactory:
    """Factory for creating model instances based on provider and configuration."""

    @staticmethod
    def create_model(provider: str, config: Dict[str, Any]):
        """
        Create a model instance based on provider and config.

        Args:
            provider: One of 'anthropic', 'bedrock', 'gemini', 'openai'
            config: Dictionary containing provider-specific configuration
                   Common keys: model_id, max_tokens, temperature, api_key

        Returns:
            Model instance for the specified provider

        Raises:
            ValueError: If provider is not supported
            KeyError: If required config keys are missing
        """

        if provider == "anthropic":
            return ModelFactory._create_anthropic(config)
        elif provider == "bedrock":
            return ModelFactory._create_bedrock(config)
        elif provider == "gemini":
            return ModelFactory._create_gemini(config)
        elif provider == "openai":
            return ModelFactory._create_openai(config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def _create_anthropic(config: Dict[str, Any]) -> AnthropicModel:
        """Create Anthropic model instance."""
        return AnthropicModel(
            client_args={
                "api_key": config.get("api_key")
            },
            model_id=config.get("model_id"),
            max_tokens=config.get("max_tokens", 64000),
            params={
                "temperature": config.get("temperature", 0.2)
            }
        )

    @staticmethod
    def _create_bedrock(config: Dict[str, Any]) -> BedrockModel:
        """Create Bedrock model instance."""
        return BedrockModel(
            model_id=config.get("model_id"),
            region_name=config.get("region_name"),
            temperature=config.get("temperature", 0.2),
            max_tokens=config.get("max_tokens", 64000),
            boto_session=config.get("boto_session")
        )

    @staticmethod
    def _create_gemini(config: Dict[str, Any]) -> GeminiModel:
        """Create Gemini model instance."""
        # Note: Gemini uses max_output_tokens instead of max_tokens
        return GeminiModel(
            client_args={
                "api_key": config.get("api_key")
            },
            model_id=config.get("model_id"),
            temperature=config.get("temperature", 0.2),
            max_output_tokens=config.get("max_tokens", 64000)
        )

    @staticmethod
    def _create_openai(config: Dict[str, Any]) -> OpenAIModel:
        """Create OpenAI model instance."""
        return OpenAIModel(
            client_args={
                "api_key": config.get("api_key")
            },
            model_id=config.get("model_id"),
            params={
                "max_tokens": config.get("max_tokens", 16000),
                "temperature": config.get("temperature", 0.2)
            }
        )
