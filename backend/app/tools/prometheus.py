"""Prometheus Metric Investigation Tool.

Provides typed, read-only query capabilities against Prometheus:
- Instant queries: evaluate PromQL at a specific point in time
- Range queries: evaluate PromQL over an interval with custom step resolution

Enforces request timeouts, input validation, and bounded result sets.
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
    MetricSample,
    MetricSeries,
    PrometheusInstantQueryInput,
    PrometheusQueryResult,
    PrometheusRangeQueryInput,
)

logger = logging.getLogger(__name__)


class PrometheusTool(BaseTelemetryTool):
    """Read-only tool querying metrics from Prometheus."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        http_client: Optional[httpx.Client] = None,
        max_results: Optional[int] = None,
    ):
        url = base_url or settings.PROMETHEUS_URL
        super().__init__(base_url=url, timeout_seconds=timeout_seconds, http_client=http_client)
        self.max_results = max_results or settings.EVIDENCE_MAX_RESULTS

    def query_instant(self, query_in: PrometheusInstantQueryInput) -> PrometheusQueryResult:
        """Execute an instant PromQL query.

        Args:
            query_in: Validated input containing PromQL query string and optional evaluation time.

        Returns:
            PrometheusQueryResult containing series and sample data points.
        """
        params: Dict[str, Any] = {"query": query_in.query}
        if query_in.time is not None:
            if isinstance(query_in.time, datetime):
                params["time"] = query_in.time.isoformat()
            else:
                params["time"] = str(query_in.time)

        response, err, elapsed_ms = self._execute_request(
            method="GET",
            path="/api/v1/query",
            params=params,
            timeout_seconds=query_in.timeout_seconds,
        )
        if err:
            return PrometheusQueryResult(
                status=err.status,
                error_message=err.error_message,
                error_type=err.error_type,
                execution_time_ms=elapsed_ms,
            )

        return self._parse_prometheus_response(response, elapsed_ms)

    def query_range(self, query_in: PrometheusRangeQueryInput) -> PrometheusQueryResult:
        """Execute a range PromQL query over a time interval.

        Args:
            query_in: Validated input with PromQL expression, start, end, and step.

        Returns:
            PrometheusQueryResult with time series matrix.
        """
        def _format_time(t: Union[datetime, float, str]) -> str:
            if isinstance(t, datetime):
                return t.isoformat()
            return str(t)

        params: Dict[str, Any] = {
            "query": query_in.query,
            "start": _format_time(query_in.start),
            "end": _format_time(query_in.end),
            "step": query_in.step,
        }

        response, err, elapsed_ms = self._execute_request(
            method="GET",
            path="/api/v1/query_range",
            params=params,
            timeout_seconds=query_in.timeout_seconds,
        )
        if err:
            return PrometheusQueryResult(
                status=err.status,
                error_message=err.error_message,
                error_type=err.error_type,
                execution_time_ms=elapsed_ms,
            )

        return self._parse_prometheus_response(response, elapsed_ms)

    def _parse_prometheus_response(
        self,
        response: httpx.Response,
        elapsed_ms: float,
    ) -> PrometheusQueryResult:
        """Parse, validate, and bound raw Prometheus JSON payload."""
        try:
            payload = response.json()
        except Exception as exc:
            return PrometheusQueryResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message=f"Failed to parse Prometheus JSON response: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )

        if not isinstance(payload, dict):
            return PrometheusQueryResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message="Prometheus response root is not a JSON object",
                execution_time_ms=elapsed_ms,
            )

        api_status = payload.get("status")
        if api_status != "success":
            err_msg = payload.get("error", "Unknown Prometheus query error")
            err_type = payload.get("errorType", "PrometheusAPIError")
            return PrometheusQueryResult(
                status=EvidenceStatus.ERROR,
                error_type=err_type,
                error_message=f"Prometheus error ({err_type}): {err_msg}",
                execution_time_ms=elapsed_ms,
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            return PrometheusQueryResult(
                status=EvidenceStatus.ERROR,
                error_type="MalformedResponseError",
                error_message="Prometheus response missing 'data' field",
                execution_time_ms=elapsed_ms,
            )

        result_type = data.get("resultType")
        raw_results = data.get("result", [])

        if not isinstance(raw_results, list) or len(raw_results) == 0:
            return PrometheusQueryResult(
                status=EvidenceStatus.EMPTY,
                result_type=result_type,
                series=[],
                series_count=0,
                execution_time_ms=elapsed_ms,
            )

        # Parse and bound metric series
        parsed_series: List[MetricSeries] = []
        is_truncated = False

        for idx, item in enumerate(raw_results):
            if idx >= self.max_results:
                is_truncated = True
                break

            if not isinstance(item, dict):
                continue

            labels = item.get("metric", {})
            values: List[MetricSample] = []

            # Vector has "value": [ts, "val"]
            if "value" in item and isinstance(item["value"], (list, tuple)) and len(item["value"]) == 2:
                try:
                    ts = float(item["value"][0])
                    val = float(item["value"][1])
                    values.append(MetricSample(timestamp=ts, value=val))
                except (ValueError, TypeError):
                    pass

            # Matrix has "values": [[ts1, "val1"], [ts2, "val2"], ...]
            elif "values" in item and isinstance(item["values"], list):
                for v in item["values"][:200]:  # bound per-series samples for safety
                    if isinstance(v, (list, tuple)) and len(v) == 2:
                        try:
                            ts = float(v[0])
                            val = float(v[1])
                            values.append(MetricSample(timestamp=ts, value=val))
                        except (ValueError, TypeError):
                            pass

            parsed_series.append(MetricSeries(labels=labels, values=values))

        status = EvidenceStatus.EMPTY if len(parsed_series) == 0 else EvidenceStatus.SUCCESS

        return PrometheusQueryResult(
            status=status,
            result_type=result_type,
            series=parsed_series,
            series_count=len(parsed_series),
            is_truncated=is_truncated,
            execution_time_ms=elapsed_ms,
        )
