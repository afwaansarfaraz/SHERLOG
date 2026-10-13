"""Loki Log Investigation Tool.

Provides typed, read-only LogQL query capabilities against Grafana Loki:
- Query application and service logs by stream selector and filter
- Bounded limit and search window controls
- Log line truncation and untrusted evidence encapsulation
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Union
import httpx

from backend.app.config import settings
from backend.app.tools.base import BaseTelemetryTool
from backend.app.tools.schemas import (
    EvidenceStatus,
    LogEntry,
    LogStream,
    LokiQueryInput,
    LokiQueryResult,
)

logger = logging.getLogger(__name__)

# Maximum characters allowed per log line to prevent unbounded memory consumption
MAX_LOG_LINE_CHARS = 4096


class LokiTool(BaseTelemetryTool):
    """Read-only tool querying application and infrastructure logs from Loki."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        http_client: Optional[httpx.Client] = None,
        max_results: Optional[int] = None,
    ):
        url = base_url or settings.LOKI_URL
        super().__init__(base_url=url, timeout_seconds=timeout_seconds, http_client=http_client)
        self.max_results = max_results or settings.EVIDENCE_MAX_RESULTS

    def query_logs(self, query_in: LokiQueryInput) -> LokiQueryResult:
        """Query logs via LogQL expression.

        Args:
            query_in: Validated input with LogQL query, limit, direction, and time window.

        Returns:
            LokiQueryResult containing matching log streams and entries.
        """
        def _to_loki_time(val: Optional[Union[datetime, str, int]]) -> Optional[str]:
            if val is None:
                return None
            if isinstance(val, datetime):
                # Loki prefers nanoseconds or RFC3339
                return str(int(val.timestamp() * 1e9))
            if isinstance(val, (int, float)):
                # If seconds, convert to nanoseconds if small
                if val < 1e11:
                    return str(int(val * 1e9))
                return str(int(val))
            return str(val)

        params: Dict[str, Any] = {
            "query": query_in.query,
            "limit": min(query_in.limit, self.max_results),
            "direction": query_in.direction,
        }
        start_ts = _to_loki_time(query_in.start)
        if start_ts:
            params["start"] = start_ts
        end_ts = _to_loki_time(query_in.end)
        if end_ts:
            params["end"] = end_ts

        # Use query_range if time window is specified or default to query_range
        response, err, elapsed_ms = self._execute_request(
            method="GET",
            path="/loki/api/v1/query_range",
            params=params,
            timeout_seconds=query_in.timeout_seconds,
        )
        if err:
            return LokiQueryResult(
                status=err.status,
                error_message=err.error_message,
                error_type=err.error_type,
                execution_time_ms=elapsed_ms,
            )

        return self._parse_loki_response(response, elapsed_ms, query_in.limit)

    def _parse_loki_response(
        self,
        response: httpx.Response,
        elapsed_ms: float,
        requested_limit: int,
    ) -> LokiQueryResult:
        """Parse and safely bound Loki stream results."""
        try:
            payload = response.json()
        except Exception as exc:
            return LokiQueryResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message=f"Failed to parse Loki JSON response: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )

        if not isinstance(payload, dict):
            return LokiQueryResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message="Loki response root is not a JSON object",
                execution_time_ms=elapsed_ms,
            )

        api_status = payload.get("status")
        if api_status != "success":
            err_msg = payload.get("error", "Unknown Loki query error")
            return LokiQueryResult(
                status=EvidenceStatus.ERROR,
                error_type="LokiAPIError",
                error_message=f"Loki error: {err_msg}",
                execution_time_ms=elapsed_ms,
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            return LokiQueryResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message="Loki response missing 'data' field",
                execution_time_ms=elapsed_ms,
            )

        raw_streams = data.get("result", [])
        if not isinstance(raw_streams, list) or len(raw_streams) == 0:
            return LokiQueryResult(
                status=EvidenceStatus.EMPTY,
                streams=[],
                total_entries=0,
                execution_time_ms=elapsed_ms,
            )

        parsed_streams: List[LogStream] = []
        total_entries = 0
        is_truncated = False

        for stream_item in raw_streams:
            if not isinstance(stream_item, dict):
                continue

            labels = stream_item.get("stream", {})
            values = stream_item.get("values", [])

            entries: List[LogEntry] = []
            if isinstance(values, list):
                for val in values:
                    if total_entries >= requested_limit:
                        is_truncated = True
                        break

                    if isinstance(val, (list, tuple)) and len(val) >= 2:
                        ts = str(val[0])
                        raw_line = str(val[1])

                        # Enforce maximum characters per log line to guard against giant payloads
                        if len(raw_line) > MAX_LOG_LINE_CHARS:
                            raw_line = raw_line[:MAX_LOG_LINE_CHARS] + " [TRUNCATED]"
                            is_truncated = True

                        entries.append(LogEntry(timestamp_ns=ts, line=raw_line))
                        total_entries += 1

            if entries:
                parsed_streams.append(LogStream(labels=labels, entries=entries))

            if total_entries >= requested_limit:
                break

        status = EvidenceStatus.EMPTY if total_entries == 0 else EvidenceStatus.SUCCESS

        return LokiQueryResult(
            status=status,
            streams=parsed_streams,
            total_entries=total_entries,
            is_truncated=is_truncated,
            execution_time_ms=elapsed_ms,
        )
