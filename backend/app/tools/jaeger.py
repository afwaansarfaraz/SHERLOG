"""Jaeger Distributed Tracing Investigation Tool.

Provides typed, read-only trace queries against Jaeger Query API:
- Retrieve individual traces by trace ID
- Search traces by service, operation, tags, duration, and time boundaries
- Structure trace spans into clean summaries with error tagging
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Union
import httpx

from backend.app.config import settings
from backend.app.tools.base import BaseTelemetryTool
from backend.app.tools.schemas import (
    EvidenceStatus,
    JaegerGetTraceInput,
    JaegerSearchTracesInput,
    JaegerTraceResult,
    SpanSummary,
    TraceSummary,
)

logger = logging.getLogger(__name__)


class JaegerTool(BaseTelemetryTool):
    """Read-only tool querying distributed traces from Jaeger."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        http_client: Optional[httpx.Client] = None,
        max_results: Optional[int] = None,
    ):
        url = base_url or settings.JAEGER_URL
        super().__init__(base_url=url, timeout_seconds=timeout_seconds, http_client=http_client)
        self.max_results = max_results or settings.EVIDENCE_MAX_RESULTS

    def get_trace(self, input_in: JaegerGetTraceInput) -> JaegerTraceResult:
        """Fetch a specific distributed trace by its unique 16-hex or 32-hex ID.

        Args:
            input_in: Validated input containing trace_id.

        Returns:
            JaegerTraceResult containing the trace hierarchy and spans.
        """
        response, err, elapsed_ms = self._execute_request(
            method="GET",
            path=f"/api/traces/{input_in.trace_id}",
            timeout_seconds=input_in.timeout_seconds,
        )
        if err:
            return JaegerTraceResult(
                status=err.status,
                error_message=err.error_message,
                error_type=err.error_type,
                execution_time_ms=elapsed_ms,
            )

        return self._parse_jaeger_response(response, elapsed_ms, limit=1)

    def search_traces(self, search_in: JaegerSearchTracesInput) -> JaegerTraceResult:
        """Search distributed traces by service, operation, tags, and duration.

        Args:
            search_in: Validated search criteria.

        Returns:
            JaegerTraceResult containing matched trace summaries.
        """
        def _to_jaeger_micros(val: Optional[Union[datetime, int, str]]) -> Optional[int]:
            if val is None:
                return None
            if isinstance(val, datetime):
                return int(val.timestamp() * 1e6)
            if isinstance(val, (int, float)):
                # If seconds, convert to microseconds
                if val < 1e11:
                    return int(val * 1e6)
                return int(val)
            try:
                dt = datetime.fromisoformat(str(val))
                return int(dt.timestamp() * 1e6)
            except Exception:
                return None

        params: Dict[str, Any] = {
            "service": search_in.service,
            "limit": min(search_in.limit, self.max_results),
        }
        if search_in.operation:
            params["operation"] = search_in.operation
        if search_in.tags:
            params["tags"] = search_in.tags
        if search_in.min_duration:
            params["minDuration"] = search_in.min_duration
        if search_in.max_duration:
            params["maxDuration"] = search_in.max_duration

        start_us = _to_jaeger_micros(search_in.start_time)
        if start_us:
            params["start"] = start_us
        end_us = _to_jaeger_micros(search_in.end_time)
        if end_us:
            params["end"] = end_us

        response, err, elapsed_ms = self._execute_request(
            method="GET",
            path="/api/traces",
            params=params,
            timeout_seconds=search_in.timeout_seconds,
        )
        if err:
            return JaegerTraceResult(
                status=err.status,
                error_message=err.error_message,
                error_type=err.error_type,
                execution_time_ms=elapsed_ms,
            )

        return self._parse_jaeger_response(response, elapsed_ms, limit=search_in.limit)

    def list_services(self) -> List[str]:
        """Retrieve list of instrumented services registered with Jaeger."""
        response, err, _ = self._execute_request(method="GET", path="/api/services")
        if err or not response:
            return []
        try:
            payload = response.json()
            return payload.get("data", []) or []
        except Exception:
            return []

    def _parse_jaeger_response(
        self,
        response: httpx.Response,
        elapsed_ms: float,
        limit: int,
    ) -> JaegerTraceResult:
        """Parse raw Jaeger JSON response into structured TraceSummary models."""
        try:
            payload = response.json()
        except Exception as exc:
            return JaegerTraceResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message=f"Failed to parse Jaeger JSON response: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )

        if not isinstance(payload, dict):
            return JaegerTraceResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message="Jaeger response root is not a JSON object",
                execution_time_ms=elapsed_ms,
            )

        raw_data = payload.get("data")
        if raw_data is None:
            errors = payload.get("errors")
            if errors:
                return JaegerTraceResult(
                    status=EvidenceStatus.ERROR,
                    error_type="JaegerAPIError",
                    error_message=f"Jaeger reported errors: {errors}",
                    execution_time_ms=elapsed_ms,
                )
            return JaegerTraceResult(
                status=EvidenceStatus.EMPTY,
                traces=[],
                total_traces=0,
                execution_time_ms=elapsed_ms,
            )

        if not isinstance(raw_data, list) or len(raw_data) == 0:
            return JaegerTraceResult(
                status=EvidenceStatus.EMPTY,
                traces=[],
                total_traces=0,
                execution_time_ms=elapsed_ms,
            )

        parsed_traces: List[TraceSummary] = []
        is_truncated = False

        for trace_idx, trace_item in enumerate(raw_data):
            if trace_idx >= limit:
                is_truncated = True
                break

            if not isinstance(trace_item, dict):
                continue

            trace_id = trace_item.get("traceID", "unknown")
            raw_spans = trace_item.get("spans", [])
            processes = trace_item.get("processes", {})

            # Map processID -> serviceName
            proc_service_map: Dict[str, str] = {}
            if isinstance(processes, dict):
                for p_id, p_info in processes.items():
                    if isinstance(p_info, dict):
                        proc_service_map[p_id] = p_info.get("serviceName", "unknown")

            spans: List[SpanSummary] = []
            error_count = 0
            root_service = None
            root_op = None
            max_duration_us = 0

            for span_data in raw_spans:
                if not isinstance(span_data, dict):
                    continue

                span_id = span_data.get("spanID", "")
                op_name = span_data.get("operationName", "")
                p_id = span_data.get("processID", "")
                svc_name = proc_service_map.get(p_id, "unknown")
                start_us = int(span_data.get("startTime", 0))
                dur_us = int(span_data.get("duration", 0))

                if dur_us > max_duration_us:
                    max_duration_us = dur_us

                # Extract and filter tags
                tags_dict: Dict[str, str] = {}
                has_error = False
                for tag in span_data.get("tags", []):
                    if isinstance(tag, dict):
                        k = str(tag.get("key", ""))
                        v = str(tag.get("value", ""))
                        tags_dict[k] = v
                        if k == "error" and v.lower() in ("true", "1"):
                            has_error = True
                        elif k == "http.status_code" and v.isdigit() and int(v) >= 500:
                            has_error = True

                if has_error:
                    error_count += 1

                # If no root identified yet, assume first span is root
                if root_service is None:
                    root_service = svc_name
                    root_op = op_name

                spans.append(
                    SpanSummary(
                        span_id=span_id,
                        operation_name=op_name,
                        service_name=svc_name,
                        start_time_us=start_us,
                        duration_us=dur_us,
                        has_error=has_error,
                        tags=tags_dict,
                    )
                )

            parsed_traces.append(
                TraceSummary(
                    trace_id=trace_id,
                    root_service=root_service,
                    root_operation=root_op,
                    duration_us=max_duration_us,
                    span_count=len(spans),
                    error_count=error_count,
                    spans=spans[:100],  # bound spans per trace for safety
                )
            )

        status = EvidenceStatus.EMPTY if len(parsed_traces) == 0 else EvidenceStatus.SUCCESS

        return JaegerTraceResult(
            status=status,
            traces=parsed_traces,
            total_traces=len(parsed_traces),
            is_truncated=is_truncated,
            execution_time_ms=elapsed_ms,
        )
