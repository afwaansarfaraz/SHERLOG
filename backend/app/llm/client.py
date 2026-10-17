"""Sherlog Groq LLM Client Module.

Provides minimal, production-grade integration with Groq's OpenAI-compatible API
using httpx. Never logs, prints, or exposes credentials.
"""

import re
import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Patterns to sanitize in any error message, exception, or logged text
_SECRET_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
]


def sanitize_secret(text: str) -> str:
    """Sanitize any API keys or Authorization headers from a string."""
    if not text:
        return ""
    sanitized = str(text)
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


class LLMError(Exception):
    """Base exception for all LLM client errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        self.status_code = status_code
        super().__init__(sanitize_secret(message))


class LLMConfigurationError(LLMError):
    """Raised when provider configuration or API key is missing or invalid."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when authentication with the provider fails (HTTP 401)."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when provider rate limits are exceeded (HTTP 429)."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM provider request times out."""
    pass


class LLMProviderUnavailableError(LLMError):
    """Raised when the LLM provider service is down or returning server errors (HTTP 5xx)."""
    pass


class LLMResponseMalformedError(LLMError):
    """Raised when the LLM provider returns invalid JSON or unexpected schema."""
    pass


class GroqClient:
    """Minimal, secure client for Groq's OpenAI-compatible REST API.
    
    Reads settings dynamically at runtime. Enforces strict credential redaction.
    """

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        base_url: Optional[str] = None,
        settings_instance: Optional[Any] = None,
    ) -> None:
        self._explicit_api_key = api_key
        self._settings = settings_instance or settings
        self.model = model or self._settings.LLM_MODEL
        self.timeout_seconds = timeout_seconds or self._settings.LLM_TIMEOUT_SECONDS
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")

    @property
    def api_key(self) -> Optional[str]:
        """Resolve API key dynamically from explicit parameter or settings."""
        if self._explicit_api_key is not None:
            return self._explicit_api_key.strip() if self._explicit_api_key else None
        return self._settings.effective_groq_api_key

    def _get_headers(self) -> Dict[str, str]:
        """Construct request headers, validating API key presence."""
        key = self.api_key
        if not key or not key.strip():
            raise LLMConfigurationError(
                "Groq API key is not configured. Set GROQ_API_KEY in the environment or .env file."
            )
        return {
            "Authorization": f"Bearer {key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "Sherlog-Incident-Investigator/1.0",
        }

    def verify_connection(self) -> Dict[str, Any]:
        """Verify API connectivity and key validity without consuming completion tokens.
        
        Calls GET /models on Groq's OpenAI-compatible endpoint.
        Returns connection metadata if successful.
        Raises typed LLMError subclasses on failure.
        """
        headers = self._get_headers()
        url = f"{self.base_url}/models"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers=headers)
                self._handle_response_status(response)

                try:
                    data = response.json()
                except Exception as json_err:
                    raise LLMResponseMalformedError(
                        f"Failed to parse provider response as JSON: {json_err}"
                    )

                models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
                model_found = self.model in models

                return {
                    "status": "connected",
                    "provider": "groq",
                    "configured_model": self.model,
                    "model_available": model_found,
                    "total_available_models": len(models),
                }

        except (httpx.ConnectError, httpx.NetworkError) as net_err:
            raise LLMProviderUnavailableError(
                f"Could not connect to Groq API endpoint: {sanitize_secret(str(net_err))}"
            )
        except httpx.TimeoutException:
            raise LLMTimeoutError(
                f"Connection to Groq API timed out after {self.timeout_seconds}s"
            )

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a chat completion request with structured error handling.
        
        Credentials are never included in error logs or exception messages.
        """
        headers = self._get_headers()
        url = f"{self.base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
                self._handle_response_status(response)

                try:
                    return response.json()
                except Exception as json_err:
                    raise LLMResponseMalformedError(
                        f"Malformed JSON in provider completion response: {json_err}"
                    )

        except (httpx.ConnectError, httpx.NetworkError) as net_err:
            raise LLMProviderUnavailableError(
                f"Could not reach Groq chat endpoint: {sanitize_secret(str(net_err))}"
            )
        except httpx.TimeoutException:
            raise LLMTimeoutError(
                f"Groq chat completion request timed out after {self.timeout_seconds}s"
            )

    def _handle_response_status(self, response: httpx.Response) -> None:
        """Evaluate HTTP response status and translate to typed LLM exceptions."""
        if response.is_success:
            return

        status = response.status_code
        try:
            error_json = response.json()
            error_msg = error_json.get("error", {}).get("message") or response.text
        except Exception:
            error_msg = response.text or f"HTTP status {status}"

        clean_msg = sanitize_secret(error_msg)

        if status == 401:
            raise LLMAuthenticationError(
                f"Groq authentication failed (HTTP 401). Invalid or revoked API key: {clean_msg}",
                status_code=401,
            )
        elif status == 429:
            raise LLMRateLimitError(
                f"Groq API rate limit exceeded (HTTP 429): {clean_msg}",
                status_code=429,
            )
        elif status >= 500:
            raise LLMProviderUnavailableError(
                f"Groq provider service error (HTTP {status}): {clean_msg}",
                status_code=status,
            )
        else:
            raise LLMError(
                f"Groq API error (HTTP {status}): {clean_msg}",
                status_code=status,
            )

    def __repr__(self) -> str:
        configured = bool(self.api_key and self.api_key.strip())
        return f"<GroqClient model='{self.model}' configured={configured} base_url='{self.base_url}'>"
