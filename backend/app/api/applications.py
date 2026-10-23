"""Application Onboarding and Monitored Service Registry API.

Provides endpoints to register, list, configure, test connection, and check telemetry
for applications monitored by Sherlog. Integrates with Prometheus, Loki, Jaeger,
and direct application health probes.
"""

from datetime import datetime, timezone
import hmac
import ipaddress
import logging
import secrets
import socket
import time
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, status
import httpcore
import httpx
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db.models.application import ApplicationModel
from backend.app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWLISTED_PROBE_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "host.docker.internal",
    "testserver",
    "api-gateway",
    "orders",
    "payments",
    "inventory",
    "notifications",
    "demo-api",
}

FORBIDDEN_METADATA_HOSTS = {
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
}

FORBIDDEN_METADATA_IPS = [
    ipaddress.ip_network("169.254.0.0/16"),   # IPv4 link-local & cloud metadata
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
]


def validate_probe_url(url: str) -> str:
    """Validate that endpoint URL is safe for active HTTP probing and return the validated IP address."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Endpoint URL must use HTTP or HTTPS scheme.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Endpoint URL must include a valid hostname.")

    hostname_lower = hostname.lower()

    # Reject cloud metadata hostnames
    if hostname_lower in FORBIDDEN_METADATA_HOSTS:
        raise ValueError("Probing cloud metadata endpoints is prohibited.")

    # Check if direct IP
    try:
        ip_obj = ipaddress.ip_address(hostname_lower)
        for net in FORBIDDEN_METADATA_IPS:
            if ip_obj in net:
                raise ValueError(f"Probing IP address {hostname} in restricted metadata range {net} is prohibited.")
        if (ip_obj.is_private or ip_obj.is_loopback) and hostname_lower not in ALLOWLISTED_PROBE_HOSTS:
            raise ValueError(f"Probing non-allowlisted private address {hostname} is prohibited.")
        return hostname_lower
    except ValueError as e:
        if "prohibited" in str(e).lower():
            raise
        # Hostname is a domain name, not a raw IP address

    # Resolve hostname to verify destination IP address
    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host {hostname}: {exc}") from exc

    if not resolved_ips:
        raise ValueError(f"Could not resolve host {hostname}")

    validated_ip: Optional[str] = None
    for _, _, _, _, sockaddr in resolved_ips:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            for net in FORBIDDEN_METADATA_IPS:
                if ip_obj in net:
                    raise ValueError(f"Probing IP address {ip_str} in restricted range {net} is prohibited.")
            if (ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_loopback) and hostname_lower not in ALLOWLISTED_PROBE_HOSTS:
                raise ValueError(f"Probing DNS-resolved host {hostname} ({ip_str}) in non-allowlisted private range is prohibited.")
            if validated_ip is None:
                validated_ip = ip_str
        except ValueError as exc:
            if "prohibited" in str(exc).lower():
                raise

    if not validated_ip:
        raise ValueError(f"Could not determine valid IP address for {hostname}")

    return validated_ip


class PinnedSyncBackend(httpcore.SyncBackend):
    """Enforces connecting only to a pre-validated IP address and rejects forbidden peer ranges."""

    def __init__(self, target_host: str, target_ip: str):
        super().__init__()
        self.target_host = target_host.lower()
        self.target_ip = target_ip

    def connect_tcp(self, host: str, port: int, *args, **kwargs):
        connect_to = self.target_ip if host.lower() == self.target_host else host
        # Reject connection if the connected peer address is in a forbidden range
        try:
            ip_obj = ipaddress.ip_address(connect_to)
            for net in FORBIDDEN_METADATA_IPS:
                if ip_obj in net:
                    raise ValueError(f"Connection to metadata address {connect_to} blocked.")
            if (ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_loopback) and host.lower() not in ALLOWLISTED_PROBE_HOSTS:
                raise ValueError(f"Connection to non-allowlisted private address {connect_to} blocked.")
        except ValueError as exc:
            if "blocked" in str(exc):
                raise
        return super().connect_tcp(connect_to, port, *args, **kwargs)


class PinnedHTTPTransport(httpx.HTTPTransport):
    """HTTP transport that connects only to the validated IP while preserving host for headers and TLS."""

    def __init__(self, target_host: str, target_ip: str, **kwargs):
        super().__init__(**kwargs)
        self._pool = httpcore.ConnectionPool(
            ssl_context=self._pool._ssl_context,
            max_connections=self._pool._max_connections,
            max_keepalive_connections=self._pool._max_keepalive_connections,
            keepalive_expiry=self._pool._keepalive_expiry,
            http1=self._pool._http1,
            http2=self._pool._http2,
            network_backend=PinnedSyncBackend(target_host, target_ip),
        )


def require_probe_authentication(
    authorization: Optional[str] = Header(default=None),
) -> None:
    """Require authentication for network probe endpoint.
    
    Fails closed with HTTP 503 when settings.API_KEY is unset.
    """
    if not settings.API_KEY or not settings.API_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application probe authentication is not configured on the server.",
        )

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to perform network probes.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    expected = settings.API_KEY.strip()
    if not hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication credentials.",
        )


# ==============================================================================
# Request / Response Schemas
# ==============================================================================

class ApplicationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Display name of the application")
    service_name: str = Field(
        ...,
        min_length=2,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_\-\.]+$",
        description="Safe service identifier matching telemetry labels (e.g. 'orders', 'api-gateway')",
    )
    environment: Literal["production", "staging", "development", "test"] = "production"
    integration_type: Literal[
        "opentelemetry", "prometheus", "loki", "jaeger", "health_probe", "custom"
    ] = "opentelemetry"
    endpoint_url: Optional[str] = Field(default=None, description="Health or metrics scrape endpoint URL")
    telemetry_config: Dict[str, Any] = Field(default_factory=dict, description="Custom integration parameters")

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            v_clean = v.strip()
            validate_probe_url(v_clean)
            return v_clean
        return None


class ConnectionTestResult(BaseModel):
    app_id: str
    status: str = Field(..., description="CONNECTED, ACTIVE_TELEMETRY, DISCONNECTED, or ERROR")
    is_connected: bool
    latency_ms: Optional[float] = None
    http_status: Optional[int] = None
    observable_telemetry_detected: bool = False
    telemetry_summary: Dict[str, Any] = Field(default_factory=dict)
    message: str
    error: Optional[str] = None
    tested_at: str


class ApplicationResponse(BaseModel):
    id: str
    name: str
    service_name: str
    environment: str
    integration_type: str
    endpoint_url: Optional[str] = None
    telemetry_config: Dict[str, Any] = Field(default_factory=dict)
    status: str
    last_checked_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    instrumentation_instructions: Optional[Dict[str, Any]] = None


# ==============================================================================
# Helpers
# ==============================================================================

def _get_instrumentation_instructions(service_name: str, integration_type: str) -> Dict[str, Any]:
    """Generate precise instrumentation snippets based on integration type."""
    return {
        "opentelemetry": {
            "title": "OpenTelemetry (OTLP) Traces & Metrics",
            "otlp_grpc_endpoint": "http://localhost:4317",
            "otlp_http_endpoint": "http://localhost:4318/v1/traces",
            "env_vars": {
                "OTEL_SERVICE_NAME": service_name,
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            },
            "sdk_guide": f"Export spans with service.name='{service_name}'. Traces will be indexed in Jaeger UI automatically.",
        },
        "prometheus": {
            "title": "Prometheus Metrics Scrape",
            "scrape_endpoint": f"http://localhost:8000/metrics (or container endpoint)",
            "required_labels": {"service": service_name},
            "sample_metrics": [f"http_requests_total{{service='{service_name}'}}", f"process_cpu_seconds_total{{service='{service_name}'}}"],
            "sdk_guide": f"Expose Prometheus metrics on /metrics with label service='{service_name}'.",
        },
        "loki": {
            "title": "Loki Structured Log Shipping",
            "loki_push_endpoint": "http://localhost:3100/loki/api/v1/push",
            "log_stream_labels": {"service": service_name, "env": "production"},
            "sdk_guide": f"Ship container logs with label stream service='{service_name}'.",
        },
        "health_probe": {
            "title": "Active Health Check Probe",
            "method": "HTTP GET",
            "expected_status": "200-299",
            "sdk_guide": "Expose an HTTP /health endpoint returning 200 OK when operational.",
        },
        "custom": {
            "title": "Custom Service Telemetry",
            "sdk_guide": f"Export metrics or logs with service identifier '{service_name}'. Use Sherlog OTel/Prometheus ingest endpoints.",
        },
    }.get(integration_type, {
        "title": "Generic Service Telemetry",
        "sdk_guide": f"Configure telemetry exporters with service identifier '{service_name}'.",
    })


def seed_default_applications(db: Session) -> None:
    """Pre-seed default demo applications once on startup if table is empty.
    
    Sets initial status to 'CONFIGURED' and leaves last_success_at unset.
    """
    existing_count = db.query(ApplicationModel).count()
    if existing_count > 0:
        return

    now = datetime.now(timezone.utc)
    demo_apps = [
        ApplicationModel(
            id="app-api-production",
            name="Storefront API Gateway",
            service_name="api",
            environment="production",
            integration_type="opentelemetry",
            endpoint_url="http://localhost:8000/health",
            telemetry_config={"port": 8000, "metrics_path": "/metrics"},
            status="CONFIGURED",
            last_checked_at=None,
            last_success_at=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        ),
        ApplicationModel(
            id="app-orders-production",
            name="Orders Core Service",
            service_name="orders",
            environment="production",
            integration_type="prometheus",
            endpoint_url="http://localhost:8001/health",
            telemetry_config={"port": 8001, "metrics_path": "/metrics"},
            status="CONFIGURED",
            last_checked_at=None,
            last_success_at=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        ),
        ApplicationModel(
            id="app-payments-production",
            name="Payments Processing Engine",
            service_name="payments",
            environment="production",
            integration_type="opentelemetry",
            endpoint_url="http://localhost:8002/health",
            telemetry_config={"port": 8002, "metrics_path": "/metrics"},
            status="CONFIGURED",
            last_checked_at=None,
            last_success_at=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        ),
    ]
    for app in demo_apps:
        db.add(app)
    db.commit()


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get(
    "",
    response_model=List[ApplicationResponse],
    summary="List all registered applications and monitored services",
)
def list_applications(db: Session = Depends(get_db)) -> List[ApplicationResponse]:
    """Retrieve all registered applications with their live telemetry configuration."""
    apps = db.query(ApplicationModel).order_by(ApplicationModel.created_at.desc()).all()
    
    results = []
    for app in apps:
        inst = _get_instrumentation_instructions(app.service_name, app.integration_type)
        results.append(
            ApplicationResponse(
                id=app.id,
                name=app.name,
                service_name=app.service_name,
                environment=app.environment,
                integration_type=app.integration_type,
                endpoint_url=app.endpoint_url,
                telemetry_config=app.telemetry_config or {},
                status=app.status,
                last_checked_at=app.last_checked_at,
                last_success_at=app.last_success_at,
                last_error=app.last_error,
                created_at=app.created_at,
                updated_at=app.updated_at,
                instrumentation_instructions=inst,
            )
        )
    return results


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new application for monitoring",
)
def register_application(
    req: ApplicationCreateRequest,
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    """Register a new application or service in the Sherlog platform inventory."""
    norm_service = req.service_name.strip().lower()
    norm_env = req.environment.strip().lower()

    # Check duplicate service name scoped to environment
    existing = (
        db.query(ApplicationModel)
        .filter(
            ApplicationModel.service_name == norm_service,
            ApplicationModel.environment == norm_env,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An application with service name '{norm_service}' in environment '{norm_env}' already exists (ID: {existing.id})",
        )

    now = datetime.now(timezone.utc)
    app_id = f"app-{norm_service}-{norm_env}-{secrets.token_hex(4)}"
    
    new_app = ApplicationModel(
        id=app_id,
        name=req.name.strip(),
        service_name=norm_service,
        environment=norm_env,
        integration_type=req.integration_type,
        endpoint_url=req.endpoint_url.strip() if req.endpoint_url else None,
        telemetry_config=req.telemetry_config or {},
        status="CONFIGURED",
        created_at=now,
        updated_at=now,
    )
    try:
        db.add(new_app)
        db.commit()
        db.refresh(new_app)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An application with service name '{norm_service}' in environment '{norm_env}' already exists.",
        )

    inst = _get_instrumentation_instructions(new_app.service_name, new_app.integration_type)
    return ApplicationResponse(
        id=new_app.id,
        name=new_app.name,
        service_name=new_app.service_name,
        environment=new_app.environment,
        integration_type=new_app.integration_type,
        endpoint_url=new_app.endpoint_url,
        telemetry_config=new_app.telemetry_config or {},
        status=new_app.status,
        last_checked_at=new_app.last_checked_at,
        last_success_at=new_app.last_success_at,
        last_error=new_app.last_error,
        created_at=new_app.created_at,
        updated_at=new_app.updated_at,
        instrumentation_instructions=inst,
    )


@router.get(
    "/{app_id}",
    response_model=ApplicationResponse,
    summary="Get application details and instrumentation instructions",
)
def get_application(app_id: str, db: Session = Depends(get_db)) -> ApplicationResponse:
    """Retrieve detailed configuration and status for a specific registered application."""
    app = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id}' not found",
        )
    inst = _get_instrumentation_instructions(app.service_name, app.integration_type)
    return ApplicationResponse(
        id=app.id,
        name=app.name,
        service_name=app.service_name,
        environment=app.environment,
        integration_type=app.integration_type,
        endpoint_url=app.endpoint_url,
        telemetry_config=app.telemetry_config or {},
        status=app.status,
        last_checked_at=app.last_checked_at,
        last_success_at=app.last_success_at,
        last_error=app.last_error,
        created_at=app.created_at,
        updated_at=app.updated_at,
        instrumentation_instructions=inst,
    )


@router.post(
    "/{app_id}/test-connection",
    response_model=ConnectionTestResult,
    summary="Perform live connectivity and telemetry arrival verification",
    dependencies=[Depends(require_probe_authentication)],
)
def test_application_connection(
    app_id: str,
    db: Session = Depends(get_db),
) -> ConnectionTestResult:
    """Test actual connectivity and check for observable telemetry in Prometheus, Loki, or Jaeger.
    
    Guarantees:
    - Never fabricates success.
    - Performs real HTTP probe if endpoint_url is configured.
    - Queries Prometheus, Loki, and Jaeger for real service metrics/logs/traces.
    - Updates application status in PostgreSQL.
    """
    app = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id}' not found",
        )

    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    latency_ms: Optional[float] = None
    http_status_code: Optional[int] = None
    http_probe_success = False
    probe_error: Optional[str] = None

    # 1. Real HTTP probe if endpoint is configured
    if app.endpoint_url:
        try:
            validated_ip = validate_probe_url(app.endpoint_url)
            parsed_url = urlparse(app.endpoint_url)
            target_host = parsed_url.hostname or ""
            start_time = time.perf_counter()
            transport = PinnedHTTPTransport(target_host, validated_ip)
            with httpx.Client(transport=transport, timeout=1.2, follow_redirects=False) as client:
                resp = client.get(app.endpoint_url)
                latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                http_status_code = resp.status_code
                if 200 <= resp.status_code < 400:
                    http_probe_success = True
                else:
                    probe_error = f"HTTP probe returned status code {resp.status_code}"
        except httpx.ConnectError:
            probe_error = f"Connection refused connecting to {app.endpoint_url}"
        except httpx.TimeoutException:
            probe_error = f"Connection timed out connecting to {app.endpoint_url}"
        except ValueError as exc:
            probe_error = f"Probe rejected: {str(exc)}"
        except Exception as exc:
            probe_error = f"Probe failed: {str(exc)}"

    # 2. Check for real observable telemetry in Prometheus
    telemetry_summary = {"prometheus_series": 0, "loki_logs": 0, "jaeger_traces": False}
    has_telemetry = False

    try:
        with httpx.Client(timeout=1.0) as client:
            prom_query = f'{{service="{app.service_name}"}}'
            prom_res = client.get(f"{settings.PROMETHEUS_URL}/api/v1/query", params={"query": prom_query})
            if prom_res.status_code == 200:
                result_data = prom_res.json().get("data", {}).get("result", [])
                telemetry_summary["prometheus_series"] = len(result_data)
                if len(result_data) > 0:
                    has_telemetry = True
    except Exception:
        pass

    # 3. Check for real observable logs in Loki
    try:
        with httpx.Client(timeout=1.0) as client:
            loki_res = client.get(f"{settings.LOKI_URL}/loki/api/v1/query_range", params={"query": f'{{service="{app.service_name}"}}', "limit": 5})
            if loki_res.status_code == 200:
                streams = loki_res.json().get("data", {}).get("result", [])
                total_lines = sum(len(s.get("values", [])) for s in streams)
                telemetry_summary["loki_logs"] = total_lines
                if total_lines > 0:
                    has_telemetry = True
    except Exception:
        pass

    # 4. Check for service registration in Jaeger
    try:
        with httpx.Client(timeout=1.0) as client:
            jaeger_res = client.get(f"{settings.JAEGER_URL}/api/services")
            if jaeger_res.status_code == 200:
                services_list = jaeger_res.json().get("data", [])
                if app.service_name in services_list:
                    telemetry_summary["jaeger_traces"] = True
                    has_telemetry = True
    except Exception:
        pass

    # Determine status
    if has_telemetry:
        determined_status = "ACTIVE_TELEMETRY"
        is_connected = True
        msg = f"Application '{app.name}' is actively emitting observable telemetry ({telemetry_summary['prometheus_series']} metric series, {telemetry_summary['loki_logs']} recent logs)."
        app.last_success_at = now
        app.last_error = None
    elif http_probe_success:
        determined_status = "CONNECTED"
        is_connected = True
        msg = f"Health check probe successful ({latency_ms} ms roundtrip). Awaiting first telemetry emit."
        app.last_success_at = now
        app.last_error = None
    elif app.endpoint_url and not http_probe_success:
        determined_status = "DISCONNECTED"
        is_connected = False
        msg = f"Connection probe failed: {probe_error}"
        app.last_error = probe_error
    else:
        determined_status = "CONFIGURED"
        is_connected = False
        msg = f"Integration configured. Instrument application using instructions below to emit telemetry."
        app.last_error = None

    app.status = determined_status
    app.last_checked_at = now
    app.updated_at = now
    db.commit()

    return ConnectionTestResult(
        app_id=app.id,
        status=determined_status,
        is_connected=is_connected,
        latency_ms=latency_ms,
        http_status=http_status_code,
        observable_telemetry_detected=has_telemetry,
        telemetry_summary=telemetry_summary,
        message=msg,
        error=probe_error,
        tested_at=now_str,
    )


@router.delete(
    "/{app_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister an application",
)
def delete_application(app_id: str, db: Session = Depends(get_db)):
    """Remove a registered application from Sherlog monitoring inventory."""
    app = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id}' not found",
        )
    db.delete(app)
    db.commit()
    return None
