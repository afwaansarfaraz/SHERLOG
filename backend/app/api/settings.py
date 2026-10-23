"""Settings and Platform Configuration Status API.

Provides endpoints to inspect the live connection status, integration health,
budget guards, and masked configuration settings of the Sherlog platform.
Never exposes raw secrets or sensitive credentials.
"""

import logging
import re
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
import httpx
import redis
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.db.session import get_db
from backend.app.db.models.knowledge import KnowledgeChunkModel, KnowledgeDocumentModel
from backend.app.investigation.schemas import ExecutionBudget

logger = logging.getLogger(__name__)

router = APIRouter()


class ServiceStatusItem(BaseModel):
    name: str
    category: str
    status: str = Field(..., description="connected, unhealthy, unreachable, configured, not_configured, not_implemented")
    is_connected: bool = False
    endpoint: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class PlatformSettingsResponse(BaseModel):
    app_name: str
    environment: str
    timestamp: str
    services: Dict[str, ServiceStatusItem]
    llm: Dict[str, Any]
    rag: Dict[str, Any]
    budget_guards: Dict[str, Any]
    security: Dict[str, Any]


def _mask_secret(val: Optional[str]) -> Optional[str]:
    """Mask secret value showing only small prefix/suffix or dots."""
    if not val:
        return None
    val_str = str(val).strip()
    if len(val_str) <= 6:
        return "••••••••"
    return f"{val_str[:4]}••••••••{val_str[-3:]}"


def _sanitize_url(raw_url: str) -> str:
    """Strip password/credentials from a URL string."""
    try:
        parsed = urlparse(raw_url)
        if parsed.password:
            netloc = f"{parsed.username or ''}:***@{parsed.hostname or ''}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return parsed._replace(netloc=netloc).geturl()
        return raw_url
    except Exception:
        return re.sub(r":([^/@]+)@", ":***@", raw_url)


@router.get(
    "/status",
    response_model=PlatformSettingsResponse,
    summary="Get platform configuration and live integration health status",
)
def get_platform_settings_status(db: Session = Depends(get_db)) -> PlatformSettingsResponse:
    """Inspect live health and configuration of all platform integrations.
    
    Guarantees:
    - Never exposes raw secrets, passwords, or tokens.
    - Tests actual connectivity to PostgreSQL and Redis.
    - Tests observability endpoints (Prometheus, Loki, Jaeger) with safe timeouts.
    - Distinguishes clearly between connected, unreachable, configured, and not_implemented.
    """
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    services: Dict[str, ServiceStatusItem] = {}

    # 1. PostgreSQL Check
    pg_sanitized = _sanitize_url(settings.DATABASE_URL)
    pg_start = time.perf_counter()
    try:
        db.execute(text("SELECT 1")).scalar()
        pg_latency = round((time.perf_counter() - pg_start) * 1000.0, 2)
        services["postgres"] = ServiceStatusItem(
            name="PostgreSQL",
            category="datastore",
            status="connected",
            is_connected=True,
            endpoint=pg_sanitized,
            latency_ms=pg_latency,
            details={
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            },
        )
    except Exception as exc:
        logger.warning("PostgreSQL ping failed: %s", exc)
        services["postgres"] = ServiceStatusItem(
            name="PostgreSQL",
            category="datastore",
            status="unhealthy",
            is_connected=False,
            endpoint=pg_sanitized,
            error=str(exc)[:150],
        )

    # 2. Redis Check
    redis_sanitized = _sanitize_url(settings.REDIS_URL)
    redis_start = time.perf_counter()
    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=1.5, socket_connect_timeout=1.5)
        r.ping()
        redis_latency = round((time.perf_counter() - redis_start) * 1000.0, 2)
        services["redis"] = ServiceStatusItem(
            name="Redis",
            category="datastore",
            status="connected",
            is_connected=True,
            endpoint=redis_sanitized,
            latency_ms=redis_latency,
            details={
                "stream_name": settings.REDIS_STREAM_NAME,
                "consumer_group": settings.REDIS_CONSUMER_GROUP,
                "dlq_stream": settings.REDIS_DLQ_STREAM_NAME,
            },
        )
    except Exception as exc:
        logger.warning("Redis ping failed: %s", exc)
        services["redis"] = ServiceStatusItem(
            name="Redis",
            category="datastore",
            status="unreachable",
            is_connected=False,
            endpoint=redis_sanitized,
            error=str(exc)[:150],
        )

    # 3. Prometheus Check
    prom_start = time.perf_counter()
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{settings.PROMETHEUS_URL}/-/healthy")
            prom_latency = round((time.perf_counter() - prom_start) * 1000.0, 2)
            if resp.status_code == 200:
                services["prometheus"] = ServiceStatusItem(
                    name="Prometheus",
                    category="observability",
                    status="connected",
                    is_connected=True,
                    endpoint=settings.PROMETHEUS_URL,
                    latency_ms=prom_latency,
                )
            else:
                services["prometheus"] = ServiceStatusItem(
                    name="Prometheus",
                    category="observability",
                    status="unhealthy",
                    is_connected=False,
                    endpoint=settings.PROMETHEUS_URL,
                    error=f"HTTP {resp.status_code}",
                )
    except Exception as exc:
        services["prometheus"] = ServiceStatusItem(
            name="Prometheus",
            category="observability",
            status="unreachable",
            is_connected=False,
            endpoint=settings.PROMETHEUS_URL,
            error="Connection refused or timed out",
        )

    # 4. Loki Check
    loki_start = time.perf_counter()
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{settings.LOKI_URL}/ready")
            loki_latency = round((time.perf_counter() - loki_start) * 1000.0, 2)
            if resp.status_code == 200:
                services["loki"] = ServiceStatusItem(
                    name="Loki",
                    category="observability",
                    status="connected",
                    is_connected=True,
                    endpoint=settings.LOKI_URL,
                    latency_ms=loki_latency,
                )
            else:
                services["loki"] = ServiceStatusItem(
                    name="Loki",
                    category="observability",
                    status="unhealthy",
                    is_connected=False,
                    endpoint=settings.LOKI_URL,
                    error=f"HTTP {resp.status_code}",
                )
    except Exception as exc:
        services["loki"] = ServiceStatusItem(
            name="Loki",
            category="observability",
            status="unreachable",
            is_connected=False,
            endpoint=settings.LOKI_URL,
            error="Connection refused or timed out",
        )

    # 5. Jaeger Check
    jaeger_start = time.perf_counter()
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{settings.JAEGER_URL}/")
            jaeger_latency = round((time.perf_counter() - jaeger_start) * 1000.0, 2)
            if resp.status_code in (200, 301, 302):
                services["jaeger"] = ServiceStatusItem(
                    name="Jaeger UI",
                    category="observability",
                    status="connected",
                    is_connected=True,
                    endpoint=settings.JAEGER_URL,
                    latency_ms=jaeger_latency,
                )
            else:
                services["jaeger"] = ServiceStatusItem(
                    name="Jaeger UI",
                    category="observability",
                    status="unhealthy",
                    is_connected=False,
                    endpoint=settings.JAEGER_URL,
                    error=f"HTTP {resp.status_code}",
                )
    except Exception as exc:
        services["jaeger"] = ServiceStatusItem(
            name="Jaeger UI",
            category="observability",
            status="unreachable",
            is_connected=False,
            endpoint=settings.JAEGER_URL,
            error="Connection refused or timed out",
        )

    # RAG Knowledge Counts from DB
    doc_count = 0
    chunk_count = 0
    try:
        doc_count = db.query(KnowledgeDocumentModel).count()
        chunk_count = db.query(KnowledgeChunkModel).count()
    except Exception as exc:
        logger.debug("Failed counting knowledge chunks: %s", exc)

    default_budget = ExecutionBudget()

    effective_key = settings.effective_groq_api_key
    llm_info = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "is_configured": bool(effective_key),
        "api_key_masked": _mask_secret(effective_key),
        "timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
        "temperature": settings.LLM_TEMPERATURE,
        "max_retries": settings.LLM_MAX_RETRIES,
    }

    rag_info = {
        "enabled": settings.RAG_ENABLED,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "top_k": settings.RAG_TOP_K,
        "similarity_threshold": settings.RAG_SIMILARITY_THRESHOLD,
        "indexed_documents_count": doc_count,
        "indexed_chunks_count": chunk_count,
    }

    budget_info = {
        "max_steps": default_budget.max_steps,
        "max_llm_calls": default_budget.max_llm_calls,
        "max_tool_calls": default_budget.max_tool_calls,
        "max_evidence_items": default_budget.max_evidence_items,
        "max_tokens": default_budget.max_tokens,
        "max_seconds": default_budget.max_seconds,
    }

    security_info = {
        "alertmanager_webhook_configured": bool(settings.WEBHOOK_SECRET),
        "alertmanager_webhook_secret_masked": _mask_secret(settings.WEBHOOK_SECRET),
        "webhook_endpoint": "/api/v1/webhooks/alertmanager",
        "oauth_status": "not_implemented",
        "oauth_details": "OAuth 2.0 / SSO is not configured in current milestone. Local operator authentication active.",
    }

    return PlatformSettingsResponse(
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        timestamp=now_str,
        services=services,
        llm=llm_info,
        rag=rag_info,
        budget_guards=budget_info,
        security=security_info,
    )
