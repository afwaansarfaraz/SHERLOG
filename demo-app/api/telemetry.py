import asyncio
import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# Context variables for logging correlation
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")
span_id_ctx: ContextVar[str] = ContextVar("span_id", default="")

# Prometheus Metrics Definitions
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["service", "method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
INCOMING_ALERTS_TOTAL = Counter(
    "incoming_alerts_total",
    "Total alerts received from Alertmanager webhook",
    ["service", "alertname", "severity"],
)


class JsonFormatter(logging.Formatter):
    """Formats log records as structured JSON with trace correlation."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        tid = trace_id_ctx.get()
        sid = span_id_ctx.get()

        log_data = {
            "timestamp": self.formatTime(record, self.datefmt) or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": tid or None,
            "span_id": sid or None,
        }

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class LokiQueueHandler(logging.Handler):
    """Async background batching handler for Grafana Loki."""

    def __init__(self, loki_url: str, service_name: str):
        super().__init__()
        self.loki_url = loki_url.rstrip("/") + "/loki/api/v1/push"
        self.service_name = service_name
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.worker_task: Optional[asyncio.Task] = None

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            if self.queue and not self.queue.full():
                self.queue.put_nowait((record.levelname.lower(), msg))
        except Exception:
            pass

    async def start_worker(self):
        self.worker_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        client = httpx.AsyncClient(timeout=2.0)
        while True:
            try:
                batch = []
                while not self.queue.empty() and len(batch) < 50:
                    batch.append(self.queue.get_nowait())

                if batch:
                    streams_map: Dict[str, list] = {}
                    now_ns = str(int(time.time() * 1e9))
                    for level, msg in batch:
                        key = level
                        if key not in streams_map:
                            streams_map[key] = []
                        streams_map[key].append([now_ns, msg])

                    streams = [
                        {"stream": {"service": self.service_name, "level": lvl}, "values": vals}
                        for lvl, vals in streams_map.items()
                    ]

                    await client.post(
                        self.loki_url,
                        json={"streams": streams},
                        headers={"Content-Type": "application/json"},
                    )
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1.0)
        await client.aclose()


class Telemetry:
    def __init__(self, service_name: str, loki_url: str, otlp_endpoint: str):
        self.service_name = service_name
        self.loki_url = loki_url
        self.otlp_endpoint = otlp_endpoint

        # Setup OpenTelemetry
        resource = Resource.create({"service.name": service_name})
        self.tracer_provider = TracerProvider(resource=resource)
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            self.span_processor = BatchSpanProcessor(otlp_exporter)
            self.tracer_provider.add_span_processor(self.span_processor)
        except Exception as e:
            print(f"Warning: Failed to initialize OTLPSpanExporter: {e}")
        trace.set_tracer_provider(self.tracer_provider)
        self.tracer = trace.get_tracer(service_name)
        self.propagator = TraceContextTextMapPropagator()

        # Setup Logging
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(JsonFormatter(service_name))
        self.logger.addHandler(stdout_handler)

        self.loki_handler = LokiQueueHandler(loki_url, service_name)
        self.loki_handler.setFormatter(JsonFormatter(service_name))
        self.logger.addHandler(self.loki_handler)

    async def start(self):
        await self.loki_handler.start_worker()

    def get_propagation_headers(self) -> Dict[str, str]:
        carrier: Dict[str, str] = {}
        self.propagator.inject(carrier)
        return carrier

    def setup_middleware(self, app: FastAPI):
        @app.middleware("http")
        async def telemetry_middleware(request: Request, call_next):
            if request.url.path in ["/metrics", "/health", "/ready"]:
                return await call_next(request)

            start_time = time.time()
            parent_ctx = self.propagator.extract(carrier=dict(request.headers))

            endpoint = request.url.path
            span_name = f"{request.method} {endpoint}"

            with self.tracer.start_as_current_span(
                span_name,
                context=parent_ctx,
                kind=trace.SpanKind.SERVER,
            ) as span:
                span_ctx = span.get_span_context()
                tid = f"{span_ctx.trace_id:032x}" if span_ctx.trace_id else ""
                sid = f"{span_ctx.span_id:016x}" if span_ctx.span_id else ""

                t_token = trace_id_ctx.set(tid)
                s_token = span_id_ctx.set(sid)

                span.set_attribute("http.method", request.method)
                span.set_attribute("http.url", str(request.url))
                span.set_attribute("service.name", self.service_name)

                status_code = 500
                try:
                    response: Response = await call_next(request)
                    status_code = response.status_code
                    span.set_attribute("http.status_code", status_code)
                    if status_code >= 500:
                        span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))

                    response.headers["X-Trace-ID"] = tid
                    return response
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    self.logger.error(f"Request exception: {exc}", exc_info=True)
                    raise
                finally:
                    duration = time.time() - start_time
                    HTTP_REQUESTS_TOTAL.labels(
                        service=self.service_name,
                        method=request.method,
                        endpoint=endpoint,
                        status_code=str(status_code),
                    ).inc()
                    HTTP_REQUEST_DURATION_SECONDS.labels(
                        service=self.service_name,
                        method=request.method,
                        endpoint=endpoint,
                    ).observe(duration)

                    self.logger.info(
                        f"{request.method} {endpoint} {status_code} - {duration*1000:.1f}ms"
                    )

                    trace_id_ctx.reset(t_token)
                    span_id_ctx.reset(s_token)

        @app.get("/metrics")
        async def metrics():
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
