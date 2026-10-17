"""Sherlog LLM Integration Package.

Provides provider client abstractions and error hierarchy for Sherlog's AI agent loop.
"""

from backend.app.llm.client import (
    GroqClient,
    LLMError,
    LLMConfigurationError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseMalformedError,
    sanitize_secret,
)

__all__ = [
    "GroqClient",
    "LLMError",
    "LLMConfigurationError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMProviderUnavailableError",
    "LLMResponseMalformedError",
    "sanitize_secret",
]
