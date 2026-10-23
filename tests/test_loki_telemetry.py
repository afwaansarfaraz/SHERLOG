import asyncio
import importlib.util
import json
import logging
from pathlib import Path
import sys

import httpx
import pytest
from prometheus_client import REGISTRY


ROOT = Path(__file__).resolve().parents[1]
SERVICE_TELEMETRY = [
    "demo-app/orders/telemetry.py",
    "demo-app/payments/telemetry.py",
    "demo-app/api/telemetry.py",
    "fault-injector/telemetry.py",
]
PROMETHEUS_METRICS = (
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "DB_CONNECTIONS_ACTIVE",
    "DB_POOL_EXHAUSTION_ERRORS",
    "SLOW_QUERIES_TOTAL",
    "DEPENDENCY_TIMEOUTS_TOTAL",
    "INJECTED_FAULT_ACTIVE",
    "ACTIVE_FAULTS_TOTAL",
    "FAULT_STATE_GAUGE",
    "INCOMING_ALERTS_TOTAL",
)


@pytest.fixture(params=SERVICE_TELEMETRY, ids=lambda path: Path(path).parent.name)
def telemetry_module(request):
    path = ROOT / request.param
    module_name = f"test_{path.parent.name.replace('-', '_')}_telemetry"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    try:
        yield module
    finally:
        for metric_name in PROMETHEUS_METRICS:
            metric = getattr(module, metric_name, None)
            if metric is not None:
                try:
                    REGISTRY.unregister(metric)
                except KeyError:
                    pass
        sys.modules.pop(module_name, None)


class FakeLokiClient:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.payloads = []
        self.closed = False

    async def post(self, url, json, headers):
        self.payloads.append(json)
        status = self.statuses.pop(0) if self.statuses else 204
        return httpx.Response(status, request=httpx.Request("POST", url))

    async def aclose(self):
        self.closed = True


def _record(service, created, message):
    record = logging.LogRecord(
        name=service,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.created = created
    return record


def test_loki_handler_retries_and_flushes_on_shutdown(telemetry_module, monkeypatch, caplog):
    assert telemetry_module.LokiQueueHandler.SHUTDOWN_TIMEOUT_SECONDS == 3.0
    service = "fault-injector" if "fault_injector" in telemetry_module.__name__ else telemetry_module.__name__.split("_")[1]
    client = FakeLokiClient([503, 204])
    monkeypatch.setattr(telemetry_module.httpx, "AsyncClient", lambda **kwargs: client)

    handler = telemetry_module.LokiQueueHandler("http://loki:3100", service)
    handler.setFormatter(telemetry_module.JsonFormatter(service))
    trace_token = telemetry_module.trace_id_ctx.set("a" * 32)
    span_token = telemetry_module.span_id_ctx.set("b" * 16)
    first_created = 1_800_000_000.123456
    handler.emit(_record(service, first_created, "first application log"))
    handler.emit(_record(service, first_created + 0.000001, "second application log"))
    telemetry_module.span_id_ctx.reset(span_token)
    telemetry_module.trace_id_ctx.reset(trace_token)

    async def run_worker():
        await handler.start_worker()
        await handler.stop_worker()

    with caplog.at_level(logging.WARNING):
        asyncio.run(run_worker())

    assert client.closed
    assert handler.queue.empty()
    assert len(client.payloads) == 2  # Initial 503, then a successful retry.
    assert "Loki push failed; retrying attempt 1/3" in caplog.text

    stream = client.payloads[-1]["streams"][0]
    assert stream["stream"] == {"service": service, "level": "info"}
    assert [entry[0] for entry in stream["values"]] == [
        str(int(first_created * 1_000_000_000)),
        str(int((first_created + 0.000001) * 1_000_000_000)),
    ]
    lines = [json.loads(entry[1]) for entry in stream["values"]]
    assert [line["message"] for line in lines] == [
        "first application log",
        "second application log",
    ]
    assert all(line["trace_id"] == "a" * 32 for line in lines)
    assert all(line["span_id"] == "b" * 16 for line in lines)


def test_loki_handler_reports_permanent_http_errors(telemetry_module, monkeypatch, caplog):
    service = "fault-injector" if "fault_injector" in telemetry_module.__name__ else telemetry_module.__name__.split("_")[1]
    client = FakeLokiClient([400])
    monkeypatch.setattr(telemetry_module.httpx, "AsyncClient", lambda **kwargs: client)

    handler = telemetry_module.LokiQueueHandler("http://loki:3100", service)
    handler.setFormatter(telemetry_module.JsonFormatter(service))
    handler.emit(_record(service, 1_800_000_000.0, "safe test message"))

    async def run_worker():
        await handler.start_worker()
        await handler.stop_worker()

    with caplog.at_level(logging.ERROR):
        asyncio.run(run_worker())

    assert client.closed
    assert handler.queue.empty()
    assert len(client.payloads) == 1  # Do not retry a permanent 4xx response.
    assert "Loki rejected a log batch" in caplog.text
    assert "safe test message" not in caplog.text
