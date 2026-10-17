"""Targeted Unit Tests for Groq LLM Provider Integration.

Covers:
- Environment configuration loading and fallback rules
- Absence of credential exposure in settings and string representations
- Secret redaction utility
- Missing API-key handling (LLMConfigurationError)
- Authentication failure handling (LLMAuthenticationError)
- Rate limit handling (LLMRateLimitError)
- Provider outage handling (LLMProviderUnavailableError)
- Timeout handling (LLMTimeoutError)
- Malformed response handling (LLMResponseMalformedError)
- Successful connection verification (mocked)
- Successful chat completion (mocked)

All unit tests use mocked HTTP responses and do not make live network calls.
"""

import httpx
import pytest
from unittest.mock import patch, MagicMock

from backend.app.config import Settings
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


class TestGroqConfiguration:
    """Test environment configuration loading, defaults, and credential handling."""

    def test_default_configuration_values(self, monkeypatch):
        """Settings defaults should match recommended Groq configuration."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=(),
        )
        assert s.LLM_PROVIDER == "groq"
        assert s.LLM_MODEL == "openai/gpt-oss-120b"
        assert s.LLM_TIMEOUT_SECONDS == 30.0
        assert s.GROQ_API_KEY is None
        assert s.effective_groq_api_key is None
        assert s.is_llm_configured is False

    def test_groq_api_key_loading_from_environment(self, monkeypatch):
        """Settings should load GROQ_API_KEY correctly."""
        dummy_key = "gsk_testdummykey1234567890abcdef"
        monkeypatch.setenv("GROQ_API_KEY", dummy_key)

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=None,
        )
        assert s.effective_groq_api_key == dummy_key
        assert s.is_llm_configured is True

    def test_fallback_to_llm_api_key_when_groq_key_missing(self, monkeypatch):
        """If GROQ_API_KEY is unset, should fallback to LLM_API_KEY."""
        dummy_key = "gsk_genericfallbackkey12345"
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("LLM_API_KEY", dummy_key)

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=None,
        )
        assert s.effective_groq_api_key == dummy_key
        assert s.is_llm_configured is True

    def test_groq_api_key_priority_over_llm_api_key(self, monkeypatch):
        """GROQ_API_KEY must take priority over LLM_API_KEY."""
        groq_key = "gsk_primarygroqkey"
        generic_key = "gsk_secondarykey"
        monkeypatch.setenv("GROQ_API_KEY", groq_key)
        monkeypatch.setenv("LLM_API_KEY", generic_key)

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=None,
        )
        assert s.effective_groq_api_key == groq_key

    def test_safe_dict_redacts_credentials(self, monkeypatch):
        """safe_dict must redact all keys and webhook secrets."""
        monkeypatch.setenv("GROQ_API_KEY", "gsk_secret_to_redact_123")
        monkeypatch.setenv("WEBHOOK_SECRET", "whsec_supersecret_456")

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=None,
        )
        exported = s.safe_dict()
        assert exported["GROQ_API_KEY"] == "[REDACTED]"
        assert exported["WEBHOOK_SECRET"] == "[REDACTED]"
        assert "gsk_secret_to_redact_123" not in str(exported)


class TestSecretSanitization:
    """Test that API keys and authorization headers are reliably scrubbed."""

    def test_sanitize_secret_redacts_gsk_patterns(self):
        raw = "Error sending request with key gsk_AbCdEf1234567890_XYZ to endpoint"
        clean = sanitize_secret(raw)
        assert "gsk_" not in clean
        assert "[REDACTED]" in clean

    def test_sanitize_secret_redacts_bearer_tokens(self):
        raw = "Header Authorization: Bearer gsk_token123 or Bearer my_secret_token"
        clean = sanitize_secret(raw)
        assert "my_secret_token" not in clean
        assert "[REDACTED]" in clean

    def test_groq_client_repr_never_exposes_key(self):
        client = GroqClient(api_key="gsk_secretkeyvalue_do_not_leak")
        representation = repr(client)
        assert "gsk_secretkeyvalue_do_not_leak" not in representation
        assert "configured=True" in representation


class TestGroqClientMockedInteractions:
    """Test client error mapping and API communication using mocked responses."""

    def test_missing_api_key_raises_configuration_error(self, monkeypatch):
        """Attempting any request without an API key must fail fast."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        isolated_settings = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=(),
        )
        client = GroqClient(settings_instance=isolated_settings)
        with pytest.raises(LLMConfigurationError) as exc_info:
            client.verify_connection()

        assert "Groq API key is not configured" in str(exc_info.value)

    @patch("httpx.Client.get")
    def test_verify_connection_success(self, mock_get):
        """Successful verification checks model availability against GET /models."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "openai/gpt-oss-20b", "object": "model"},
                {"id": "openai/gpt-oss-120b", "object": "model"},
            ],
        }
        mock_get.return_value = mock_response

        client = GroqClient(api_key="gsk_mock_valid_key")
        result = client.verify_connection()

        assert result["status"] == "connected"
        assert result["provider"] == "groq"
        assert result["configured_model"] == "openai/gpt-oss-120b"
        assert result["model_available"] is True
        assert result["total_available_models"] == 2

    @patch("httpx.Client.get")
    def test_authentication_failure_401(self, mock_get):
        """HTTP 401 must raise LLMAuthenticationError and redact any echoed key."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"message": "Invalid API Key provided: gsk_invalid_sample_key"}
        }
        mock_get.return_value = mock_response

        client = GroqClient(api_key="gsk_mock_key")
        with pytest.raises(LLMAuthenticationError) as exc_info:
            client.verify_connection()

        assert exc_info.value.status_code == 401
        assert "Invalid or revoked API key" in str(exc_info.value)
        # Verify secret was scrubbed from exception message
        assert "gsk_invalid_sample_key" not in str(exc_info.value)

    @patch("httpx.Client.get")
    def test_rate_limit_failure_429(self, mock_get):
        """HTTP 429 must raise LLMRateLimitError."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {"message": "Rate limit reached for requests per minute (RPM)."}
        }
        mock_get.return_value = mock_response

        client = GroqClient(api_key="gsk_mock_key")
        with pytest.raises(LLMRateLimitError) as exc_info:
            client.verify_connection()

        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in str(exc_info.value).lower()

    @patch("httpx.Client.get")
    def test_provider_outage_503(self, mock_get):
        """HTTP 503 must raise LLMProviderUnavailableError."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 503
        mock_response.text = "Service Temporarily Unavailable"
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_get.return_value = mock_response

        client = GroqClient(api_key="gsk_mock_key")
        with pytest.raises(LLMProviderUnavailableError) as exc_info:
            client.verify_connection()

        assert exc_info.value.status_code == 503
        assert "provider service error" in str(exc_info.value).lower()

    @patch("httpx.Client.get")
    def test_timeout_exception(self, mock_get):
        """httpx.TimeoutException must raise LLMTimeoutError."""
        mock_get.side_effect = httpx.TimeoutException("Read timeout after 30s")

        client = GroqClient(api_key="gsk_mock_key", timeout_seconds=10.0)
        with pytest.raises(LLMTimeoutError) as exc_info:
            client.verify_connection()

        assert "timed out" in str(exc_info.value).lower()

    @patch("httpx.Client.get")
    def test_malformed_json_response(self, mock_get):
        """200 OK with non-JSON payload must raise LLMResponseMalformedError."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON string")
        mock_get.return_value = mock_response

        client = GroqClient(api_key="gsk_mock_key")
        with pytest.raises(LLMResponseMalformedError) as exc_info:
            client.verify_connection()

        assert "Failed to parse provider response as JSON" in str(exc_info.value)

    @patch("httpx.Client.post")
    def test_chat_completion_success(self, mock_post):
        """Successful chat completion returns model output."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-test-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Database pool exhaustion is the root cause.",
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 15, "total_tokens": 115},
        }
        mock_post.return_value = mock_response

        client = GroqClient(api_key="gsk_mock_key")
        res = client.create_chat_completion(
            messages=[{"role": "user", "content": "Diagnose incident INC-001"}]
        )

        assert res["id"] == "chatcmpl-test-123"
        assert res["choices"][0]["message"]["content"] == "Database pool exhaustion is the root cause."
        assert res["usage"]["total_tokens"] == 115


class TestEnvironmentLoadingRegression:
    """Regression tests for project-root .env resolution and missing-key handling."""

    def test_root_env_file_configured_in_model_config(self):
        """Settings model_config must include ROOT_ENV_FILE for CWD independence."""
        from backend.app.config import ROOT_ENV_FILE, Settings
        env_files = Settings.model_config.get("env_file")
        assert env_files is not None
        assert str(ROOT_ENV_FILE) in env_files or ROOT_ENV_FILE in env_files

    def test_is_llm_configured_false_when_keys_missing(self, monkeypatch):
        """When keys are absent, is_llm_configured must be False and connection fail fast."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=(),
        )
        assert s.is_llm_configured is False
        assert s.effective_groq_api_key is None

        client = GroqClient(settings_instance=s)
        with pytest.raises(LLMConfigurationError) as exc:
            client.verify_connection()
        assert "Groq API key is not configured" in str(exc.value)

    def test_empty_or_whitespace_key_is_falsy(self, monkeypatch):
        """Whitespace or empty strings must be treated as unconfigured."""
        monkeypatch.setenv("GROQ_API_KEY", "   ")
        monkeypatch.setenv("LLM_API_KEY", "")

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=(),
        )
        assert s.is_llm_configured is False
        assert s.effective_groq_api_key is None

    def test_runtime_os_environ_precedence_over_settings(self, monkeypatch):
        """os.environ dynamically takes precedence over preexisting Settings fields."""
        monkeypatch.setenv("GROQ_API_KEY", "gsk_live_override_key")

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            GROQ_API_KEY="gsk_stale_settings_key",
            _env_file=None,
        )
        assert s.effective_groq_api_key == "gsk_live_override_key"

    def test_groq_key_precedence_over_generic_llm_key(self, monkeypatch):
        """GROQ_API_KEY takes precedence over LLM_API_KEY in all cases."""
        monkeypatch.setenv("GROQ_API_KEY", "gsk_preferred_groq_key")
        monkeypatch.setenv("LLM_API_KEY", "gsk_secondary_generic_key")

        s = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=None,
        )
        assert s.effective_groq_api_key == "gsk_preferred_groq_key"

    def test_groq_client_resolves_key_dynamically_from_environ(self, monkeypatch):
        """GroqClient().api_key dynamically resolves newly set environment variables."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        isolated_settings = Settings(
            DATABASE_URL="postgresql://test:test@localhost:5432/test",
            _env_file=(),
        )
        client = GroqClient(settings_instance=isolated_settings)
        assert client.api_key is None

        # Dynamically inject key into environment
        monkeypatch.setenv("GROQ_API_KEY", "gsk_dynamically_injected_key")
        assert client.api_key == "gsk_dynamically_injected_key"

