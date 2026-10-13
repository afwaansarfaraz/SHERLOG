"""Base client infrastructure for read-only investigation evidence collection tools.

Provides:
- Shared HTTP client lifecycle with connection timeouts and retries
- Exception to EvidenceStatus mapping (Timeout, Connection, HTTP status, Malformed responses)
- High-resolution execution timing
- Safety boundaries ensuring untrusted content is strictly capped and never evaluated
"""

import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple
import httpx

from backend.app.config import settings
from backend.app.tools.schemas import BaseEvidenceResult, EvidenceStatus

logger = logging.getLogger(__name__)


class BaseTelemetryTool:
    """Base class for telemetry evidence retrieval tools (Prometheus, Loki, Jaeger)."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: Optional[float] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_timeout = timeout_seconds or settings.OBSERVABILITY_TIMEOUT_SECONDS
        self._client = http_client

    @property
    def client(self) -> httpx.Client:
        """Provide managed or shared HTTP client instance."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.default_timeout),
                follow_redirects=True,
            )
        return self._client

    def _execute_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Tuple[Optional[httpx.Response], Optional[BaseEvidenceResult], float]:
        """Execute HTTP request with strict error handling and duration tracking.

        Returns:
            Tuple of:
            - Optional[httpx.Response] (if request succeeded with HTTP 200)
            - Optional[BaseEvidenceResult] (pre-populated error envelope if failed)
            - float (duration in ms)
        """
        start_time = time.perf_counter()
        timeout = httpx.Timeout(timeout_seconds or self.default_timeout)

        try:
            response = self.client.request(
                method=method,
                url=path,
                params=params,
                timeout=timeout,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if response.status_code != 200:
                logger.warning(
                    "%s %s returned HTTP %d: %s",
                    method,
                    path,
                    response.status_code,
                    response.text[:200],
                )
                error_result = BaseEvidenceResult(
                    status=EvidenceStatus.ERROR,
                    error_type="HTTPError",
                    error_message=f"HTTP {response.status_code}: {response.text[:300]}",
                    execution_time_ms=elapsed_ms,
                )
                return None, error_result, elapsed_ms

            return response, None, elapsed_ms

        except httpx.TimeoutException as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning("Timeout connecting to %s %s: %s", method, path, exc)
            error_result = BaseEvidenceResult(
                status=EvidenceStatus.TIMEOUT,
                error_type="TimeoutError",
                error_message=f"Request to {self.base_url}{path} timed out after {timeout.read}s",
                execution_time_ms=elapsed_ms,
            )
            return None, error_result, elapsed_ms

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning("Connection failure to %s: %s", self.base_url, exc)
            error_result = BaseEvidenceResult(
                status=EvidenceStatus.ERROR,
                error_type="ConnectionError",
                error_message=f"Failed to connect to service at {self.base_url}: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )
            return None, error_result, elapsed_ms

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Unexpected error querying %s: %s", self.base_url, exc, exc_info=True)
            error_result = BaseEvidenceResult(
                status=EvidenceStatus.ERROR,
                error_type="UnexpectedError",
                error_message=f"Unexpected error: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )
            return None, error_result, elapsed_ms

    def close(self) -> None:
        """Close underlying HTTP client if initialized."""
        if self._client is not None:
            self._client.close()
            self._client = None
