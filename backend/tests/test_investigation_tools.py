"""Comprehensive unit tests for typed investigation tools.

Tests:
- Prometheus metric queries (instant, range, empty, malformed, timeout, connection error, bounds)
- Loki log queries (streams, empty, malformed, timeout, connection error, line truncation)
- Jaeger trace retrieval (get by ID, search, empty, malformed, timeout, connection error)
- Git history & configuration diffs (log, diff, show, not found, timeout, path traversal defense)
"""

from datetime import datetime, timezone
import json
import subprocess
from unittest.mock import MagicMock, patch
import pytest
import httpx
from pydantic import ValidationError

from backend.app.tools.schemas import (
    EvidenceStatus,
    GitDiffInput,
    GitLogInput,
    GitShowInput,
    JaegerGetTraceInput,
    JaegerSearchTracesInput,
    LokiQueryInput,
    PrometheusInstantQueryInput,
    PrometheusRangeQueryInput,
)
from backend.app.tools.prometheus import PrometheusTool
from backend.app.tools.loki import LokiTool
from backend.app.tools.jaeger import JaegerTool
from backend.app.tools.git import GitTool


# ==============================================================================
# 1. PROMETHEUS TOOL TESTS
# ==============================================================================

def test_prometheus_instant_query_success():
    """PrometheusTool must parse instant vector responses into typed MetricSeries."""
    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"__name__": "http_requests_total", "service": "orders", "status_code": "500"},
                    "value": [1712345678.123, "42.5"],
                },
                {
                    "metric": {"__name__": "http_requests_total", "service": "payments", "status_code": "200"},
                    "value": [1712345678.123, "150.0"],
                },
            ],
        },
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = httpx.Response(status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test"))
    mock_client.request.return_value = mock_resp

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client)
    res = tool.query_instant(PrometheusInstantQueryInput(query="http_requests_total"))

    assert res.status == EvidenceStatus.SUCCESS
    assert res.result_type == "vector"
    assert res.series_count == 2
    assert len(res.series) == 2
    assert res.series[0].labels["service"] == "orders"
    assert res.series[0].values[0].value == 42.5
    assert res.series[0].values[0].timestamp == 1712345678.123
    assert not res.is_truncated
    assert res.execution_time_ms >= 0


def test_prometheus_range_query_success():
    """PrometheusTool must parse matrix results over time ranges."""
    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"service": "orders"},
                    "values": [
                        [1712345600.0, "10.0"],
                        [1712345615.0, "15.0"],
                        [1712345630.0, "25.0"],
                    ],
                }
            ],
        },
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = httpx.Response(status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test"))
    mock_client.request.return_value = mock_resp

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client)
    res = tool.query_range(
        PrometheusRangeQueryInput(
            query="rate(db_pool_exhaustion_errors_total[1m])",
            start=1712345600.0,
            end=1712345630.0,
            step="15s",
        )
    )

    assert res.status == EvidenceStatus.SUCCESS
    assert res.result_type == "matrix"
    assert res.series_count == 1
    assert len(res.series[0].values) == 3
    assert res.series[0].values[2].value == 25.0


def test_prometheus_empty_result():
    """When Prometheus returns 0 matching series, tool must report EvidenceStatus.EMPTY."""
    mock_payload = {
        "status": "success",
        "data": {"resultType": "vector", "result": []},
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client)
    res = tool.query_instant(PrometheusInstantQueryInput(query="nonexistent_metric"))

    assert res.status == EvidenceStatus.EMPTY
    assert res.series_count == 0
    assert len(res.series) == 0


def test_prometheus_malformed_response():
    """Malformed non-JSON or invalid schema response must be captured as MalformedResponseError."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = httpx.Response(
        status_code=200, text="not a valid json string", request=httpx.Request("GET", "http://test")
    )
    mock_client.request.return_value = mock_resp

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client)
    res = tool.query_instant(PrometheusInstantQueryInput(query="any_query"))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "MalformedResponseError"
    assert "Failed to parse Prometheus JSON" in (res.error_message or "")


def test_prometheus_api_error_response():
    """Prometheus error status (e.g. invalid promql syntax) must yield EvidenceStatus.ERROR."""
    mock_payload = {
        "status": "error",
        "errorType": "bad_data",
        "error": "1:23: parse error: unexpected character inside expression",
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client)
    res = tool.query_instant(PrometheusInstantQueryInput(query="invalid((syntax"))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "bad_data"
    assert "parse error" in (res.error_message or "")


def test_prometheus_timeout():
    """HTTP client timeout must return EvidenceStatus.TIMEOUT without unhandled exception."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.ReadTimeout("Read timed out")

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client)
    res = tool.query_instant(PrometheusInstantQueryInput(query="rate(heavy_query[1h])"))

    assert res.status == EvidenceStatus.TIMEOUT
    assert res.error_type == "TimeoutError"
    assert "timed out" in (res.error_message or "").lower()


def test_prometheus_connection_error():
    """Unreachable Prometheus service must return EvidenceStatus.ERROR with ConnectionError."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.ConnectError("Connection refused on 9090")

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client)
    res = tool.query_instant(PrometheusInstantQueryInput(query="up"))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "ConnectionError"
    assert "Failed to connect" in (res.error_message or "")


def test_prometheus_bounded_results():
    """Result sets exceeding max_results limit must be capped with is_truncated=True."""
    mock_results = [
        {"metric": {"id": str(i)}, "value": [1712345678.0, str(i)]}
        for i in range(25)
    ]
    mock_payload = {
        "status": "success",
        "data": {"resultType": "vector", "result": mock_results},
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = PrometheusTool(base_url="http://prom.mock", http_client=mock_client, max_results=5)
    res = tool.query_instant(PrometheusInstantQueryInput(query="test_metric"))

    assert res.status == EvidenceStatus.SUCCESS
    assert res.series_count == 5
    assert len(res.series) == 5
    assert res.is_truncated is True


def test_prometheus_input_validation():
    """Blank or whitespace-only PromQL queries must fail Pydantic validation."""
    with pytest.raises(ValidationError):
        PrometheusInstantQueryInput(query="   ")

    with pytest.raises(ValidationError):
        PrometheusRangeQueryInput(
            query="",
            start=100,
            end=200,
        )


# ==============================================================================
# 2. LOKI TOOL TESTS
# ==============================================================================

def test_loki_query_logs_success():
    """LokiTool must parse streams and individual log entries."""
    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"service": "orders", "level": "error"},
                    "values": [
                        ["1712345678000000000", "DB pool checkout timeout after 2.0s"],
                        ["1712345679000000000", "Failed to acquire connection for /checkout"],
                    ],
                }
            ],
        },
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = LokiTool(base_url="http://loki.mock", http_client=mock_client)
    res = tool.query_logs(LokiQueryInput(query='{service="orders"} |= "timeout"'))

    assert res.status == EvidenceStatus.SUCCESS
    assert res.total_entries == 2
    assert len(res.streams) == 1
    assert res.streams[0].labels["service"] == "orders"
    assert res.streams[0].entries[0].line == "DB pool checkout timeout after 2.0s"
    assert not res.is_truncated


def test_loki_empty_results():
    """When Loki returns no matching streams, tool returns EvidenceStatus.EMPTY."""
    mock_payload = {
        "status": "success",
        "data": {"resultType": "streams", "result": []},
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = LokiTool(base_url="http://loki.mock", http_client=mock_client)
    res = tool.query_logs(LokiQueryInput(query='{service="unknown"}'))

    assert res.status == EvidenceStatus.EMPTY
    assert res.total_entries == 0
    assert len(res.streams) == 0


def test_loki_malformed_response():
    """Malformed Loki response must be caught cleanly."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, text="not-json", request=httpx.Request("GET", "http://test")
    )

    tool = LokiTool(base_url="http://loki.mock", http_client=mock_client)
    res = tool.query_logs(LokiQueryInput(query='{service="orders"}'))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "MalformedResponseError"


def test_loki_timeout():
    """Loki request timeout returns EvidenceStatus.TIMEOUT."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.ReadTimeout("Timeout querying Loki")

    tool = LokiTool(base_url="http://loki.mock", http_client=mock_client)
    res = tool.query_logs(LokiQueryInput(query='{service="orders"}'))

    assert res.status == EvidenceStatus.TIMEOUT
    assert res.error_type == "TimeoutError"


def test_loki_connection_error():
    """Loki connection error returns EvidenceStatus.ERROR."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.ConnectError("Loki down on port 3100")

    tool = LokiTool(base_url="http://loki.mock", http_client=mock_client)
    res = tool.query_logs(LokiQueryInput(query='{service="orders"}'))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "ConnectionError"


def test_loki_log_line_truncation():
    """Extremely long log lines must be truncated to MAX_LOG_LINE_CHARS for safety."""
    huge_line = "A" * 6000
    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"service": "orders"},
                    "values": [["1712345678000000000", huge_line]],
                }
            ],
        },
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = LokiTool(base_url="http://loki.mock", http_client=mock_client)
    res = tool.query_logs(LokiQueryInput(query='{service="orders"}'))

    assert res.status == EvidenceStatus.SUCCESS
    assert res.is_truncated is True
    entry = res.streams[0].entries[0]
    assert len(entry.line) < 4200
    assert "[TRUNCATED]" in entry.line


def test_loki_input_validation():
    """Invalid LogQL or limits outside bounds must raise ValidationError."""
    with pytest.raises(ValidationError):
        LokiQueryInput(query="")

    with pytest.raises(ValidationError):
        LokiQueryInput(query='{service="orders"}', limit=0)

    with pytest.raises(ValidationError):
        LokiQueryInput(query='{service="orders"}', limit=500)  # max is 200

    with pytest.raises(ValidationError):
        LokiQueryInput(query='{service="orders"}', direction="SIDEWAYS")


# ==============================================================================
# 3. JAEGER TOOL TESTS
# ==============================================================================

def test_jaeger_get_trace_success():
    """JaegerTool must parse spans, correlate service names, and tag errors."""
    mock_payload = {
        "data": [
            {
                "traceID": "4bf92f3577b34da6a3ce929d0e0e4736",
                "spans": [
                    {
                        "traceID": "4bf92f3577b34da6a3ce929d0e0e4736",
                        "spanID": "span-1",
                        "operationName": "POST /orders",
                        "startTime": 1712345678000000,
                        "duration": 50000,
                        "tags": [
                            {"key": "http.status_code", "value": 500},
                            {"key": "error", "value": True},
                        ],
                        "processID": "p1",
                    },
                    {
                        "traceID": "4bf92f3577b34da6a3ce929d0e0e4736",
                        "spanID": "span-2",
                        "operationName": "db.checkout",
                        "startTime": 1712345678010000,
                        "duration": 20000,
                        "tags": [{"key": "db.system", "value": "postgresql"}],
                        "processID": "p1",
                    },
                ],
                "processes": {
                    "p1": {"serviceName": "orders"},
                },
            }
        ]
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = JaegerTool(base_url="http://jaeger.mock", http_client=mock_client)
    res = tool.get_trace(JaegerGetTraceInput(trace_id="4bf92f3577b34da6a3ce929d0e0e4736"))

    assert res.status == EvidenceStatus.SUCCESS
    assert res.total_traces == 1
    trace = res.traces[0]
    assert trace.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert trace.root_service == "orders"
    assert trace.root_operation == "POST /orders"
    assert trace.span_count == 2
    assert trace.error_count == 1
    assert trace.spans[0].has_error is True
    assert trace.spans[1].has_error is False


def test_jaeger_search_traces_success():
    """JaegerTool must parse multi-trace search results."""
    mock_payload = {
        "data": [
            {
                "traceID": "trace1",
                "spans": [{"spanID": "s1", "operationName": "op1", "startTime": 100, "duration": 50, "processID": "p1"}],
                "processes": {"p1": {"serviceName": "payments"}},
            },
            {
                "traceID": "trace2",
                "spans": [{"spanID": "s2", "operationName": "op2", "startTime": 200, "duration": 80, "processID": "p1"}],
                "processes": {"p1": {"serviceName": "payments"}},
            },
        ]
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = JaegerTool(base_url="http://jaeger.mock", http_client=mock_client)
    res = tool.search_traces(JaegerSearchTracesInput(service="payments", limit=10))

    assert res.status == EvidenceStatus.SUCCESS
    assert res.total_traces == 2
    assert res.traces[0].trace_id == "trace1"
    assert res.traces[1].trace_id == "trace2"


def test_jaeger_empty_result():
    """When Jaeger has no traces matching criteria, return EvidenceStatus.EMPTY."""
    mock_payload = {"data": []}
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, json=mock_payload, request=httpx.Request("GET", "http://test")
    )

    tool = JaegerTool(base_url="http://jaeger.mock", http_client=mock_client)
    res = tool.search_traces(JaegerSearchTracesInput(service="orders"))

    assert res.status == EvidenceStatus.EMPTY
    assert res.total_traces == 0


def test_jaeger_malformed_response():
    """Malformed JSON response must return MalformedResponseError."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.return_value = httpx.Response(
        status_code=200, text="<!DOCTYPE html><html>502 Bad Gateway</html>", request=httpx.Request("GET", "http://test")
    )

    tool = JaegerTool(base_url="http://jaeger.mock", http_client=mock_client)
    res = tool.get_trace(JaegerGetTraceInput(trace_id="4bf92f3577b34da6"))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "MalformedResponseError"


def test_jaeger_timeout():
    """Jaeger timeout must return EvidenceStatus.TIMEOUT."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.ReadTimeout("Jaeger request timed out")

    tool = JaegerTool(base_url="http://jaeger.mock", http_client=mock_client)
    res = tool.get_trace(JaegerGetTraceInput(trace_id="4bf92f3577b34da6"))

    assert res.status == EvidenceStatus.TIMEOUT
    assert res.error_type == "TimeoutError"


def test_jaeger_connection_error():
    """Jaeger connection failure must return EvidenceStatus.ERROR."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.request.side_effect = httpx.ConnectError("Jaeger unavailable on 16686")

    tool = JaegerTool(base_url="http://jaeger.mock", http_client=mock_client)
    res = tool.get_trace(JaegerGetTraceInput(trace_id="4bf92f3577b34da6"))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "ConnectionError"


def test_jaeger_input_validation():
    """Invalid non-hex trace IDs must fail Pydantic validation."""
    with pytest.raises(ValidationError):
        JaegerGetTraceInput(trace_id="not-a-valid-hex-trace-id!@#")


# ==============================================================================
# 4. GIT TOOL TESTS
# ==============================================================================

def test_git_get_commits_live_repository():
    """GitTool must read real commit history from the current git repository."""
    tool = GitTool()
    res = tool.get_commits(GitLogInput(max_count=5))

    assert res.status == EvidenceStatus.SUCCESS
    assert res.total_commits > 0
    first_commit = res.commits[0]
    assert len(first_commit.commit_hash) >= 40
    assert len(first_commit.short_hash) >= 7
    assert first_commit.author_name != ""
    assert first_commit.subject != ""


def test_git_show_file_live_repository():
    """GitTool must read existing committed file contents."""
    tool = GitTool()
    res = tool.show_file(GitShowInput(revision="HEAD", path="requirements.txt"))

    assert res.status == EvidenceStatus.SUCCESS
    assert "fastapi" in res.content
    assert res.lines_count > 0
    assert not res.is_truncated


def test_git_show_file_not_found():
    """Requesting non-existent file path must return GitFileNotFound error cleanly."""
    tool = GitTool()
    res = tool.show_file(GitShowInput(revision="HEAD", path="nonexistent_folder/missing_file.py"))

    assert res.status == EvidenceStatus.ERROR
    assert res.error_type == "GitFileNotFound"
    assert "not found" in (res.error_message or "").lower()


def test_git_get_diff_live_repository():
    """GitTool must execute git diff cleanly."""
    tool = GitTool()
    # Diff against HEAD~1 or HEAD
    res = tool.get_diff(GitDiffInput(commit_a="HEAD~1", commit_b="HEAD", max_lines=100))

    # Either diff content exists or it is empty (clean comparison)
    assert res.status in (EvidenceStatus.SUCCESS, EvidenceStatus.EMPTY)


def test_git_timeout_handling():
    """TimeoutExpired during git execution must return EvidenceStatus.TIMEOUT."""
    tool = GitTool()
    with patch.object(tool, "_run_git_cmd", side_effect=subprocess.TimeoutExpired(cmd=["git", "log"], timeout=5.0)):
        res = tool.get_commits(GitLogInput(max_count=5))
        assert res.status == EvidenceStatus.TIMEOUT
        assert res.error_type == "TimeoutError"


def test_git_command_error_handling():
    """Non-zero return code from git must be handled cleanly as GitCommandError."""
    tool = GitTool()
    mock_proc = subprocess.CompletedProcess(
        args=["git", "log"],
        returncode=128,
        stdout="",
        stderr="fatal: ambiguous argument 'nonexistent_branch'",
    )
    with patch.object(tool, "_run_git_cmd", return_value=mock_proc):
        res = tool.get_commits(GitLogInput(revision="nonexistent_branch"))
        assert res.status == EvidenceStatus.ERROR
        assert res.error_type == "GitCommandError"
        assert "fatal: ambiguous argument" in (res.error_message or "")


def test_git_path_traversal_defense():
    """Path traversal characters like '..' and absolute paths must be rejected by Pydantic."""
    with pytest.raises(ValidationError):
        GitLogInput(path="../../etc/passwd")

    with pytest.raises(ValidationError):
        GitShowInput(path="/etc/shadow")

    with pytest.raises(ValidationError):
        GitDiffInput(path="..\\..\\windows\\system32")


def test_git_revision_sanitization():
    """Revisions containing suspicious injection characters must be rejected."""
    with pytest.raises(ValidationError):
        GitLogInput(revision="HEAD; rm -rf /")

    with pytest.raises(ValidationError):
        GitDiffInput(commit_a="HEAD`whoami`")
