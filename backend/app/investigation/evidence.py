"""Evidence Collection module executing typed read-only telemetry tools with bounded budgets."""

from datetime import datetime, timezone
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.baseline.models import EvidenceItem, EvidenceType
from backend.app.investigation.schemas import BudgetConsumption, ExecutionBudget
from backend.app.investigation.summarizer import summarize_logs
from backend.app.tools.git import GitTool
from backend.app.tools.jaeger import JaegerTool
from backend.app.tools.loki import LokiTool
from backend.app.tools.prometheus import PrometheusTool
from backend.app.tools.schemas import (
    EvidenceStatus,
    GitLogInput,
    JaegerSearchTracesInput,
    LokiQueryInput,
    PrometheusInstantQueryInput,
)

logger = logging.getLogger(__name__)

# Injection defense pattern for sanitizing evidence before inclusion in context
_INJECTION_PATTERN = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|system\s+prompt|tool_call|sudo|system:\s*)",
    re.IGNORECASE,
)


def sanitize_untrusted_evidence_text(text: str) -> str:
    """Sanitize raw telemetry text, neutralising common prompt-injection triggers."""
    if not text:
        return ""
    clean = _INJECTION_PATTERN.sub("[FILTERED_INPUT]", str(text))
    # Escape tag delimiters to prevent prompt breakout
    clean = clean.replace("<untrusted_evidence>", "&lt;untrusted_evidence&gt;")
    clean = clean.replace("</untrusted_evidence>", "&lt;/untrusted_evidence&gt;")
    return clean


class EvidenceCollector:
    """Orchestrates typed, read-only evidence collection across Prometheus, Loki, Jaeger, and Git."""

    def __init__(
        self,
        prometheus_tool: Optional[PrometheusTool] = None,
        loki_tool: Optional[LokiTool] = None,
        jaeger_tool: Optional[JaegerTool] = None,
        git_tool: Optional[GitTool] = None,
    ):
        self.prometheus = prometheus_tool or PrometheusTool()
        self.loki = loki_tool or LokiTool()
        self.jaeger = jaeger_tool or JaegerTool()
        self.git = git_tool or GitTool()

    def collect_for_incident(
        self,
        incident: Dict[str, Any],
        budget: ExecutionBudget,
        consumption: BudgetConsumption,
    ) -> Tuple[List[EvidenceItem], List[Dict[str, Any]]]:
        """Collect bounded evidence across all observability tools for a given incident.
        
        Args:
            incident: Ingested incident alert metadata dict.
            budget: ExecutionBudget hard boundaries.
            consumption: Mutable BudgetConsumption tracker.

        Returns:
            Tuple of (collected EvidenceItem list, tool execution logs list).
        """
        service = incident.get("service", "unknown")
        incident_text = f"{incident.get('title', '')} {incident.get('summary', '')}".lower()
        is_slow_query_incident = bool(re.search(r"\bslow quer(?:y|ies)\b", incident_text))
        evidence_items: List[EvidenceItem] = []
        tool_executions: List[Dict[str, Any]] = []

        now_utc = datetime.now(timezone.utc).isoformat()

        raw_ts = incident.get("created_at")
        ts_str = raw_ts.isoformat() if isinstance(raw_ts, datetime) else (str(raw_ts) if raw_ts else now_utc)

        # 1. Alert metadata as initial confirmed evidence
        initial_alert_evidence = EvidenceItem(
            source=EvidenceType.ALERT,
            name=f"alert:{incident.get('title', 'Unknown Alert')}",
            value=sanitize_untrusted_evidence_text(incident.get("summary", "")),
            service=service,
            description="Incoming incident alert summary",
            timestamp=ts_str,
        )
        evidence_items.append(initial_alert_evidence)
        consumption.evidence_items += 1

        # Incorporate pre-packaged evidence if provided (e.g. benchmark evaluations)
        if incident.get("evidence"):
            for ev in incident.get("evidence", []):
                if isinstance(ev, EvidenceItem):
                    evidence_items.append(ev)
                elif isinstance(ev, dict):
                    src_val = ev.get("source", "metric")
                    evidence_items.append(
                        EvidenceItem(
                            source=EvidenceType(src_val) if src_val in EvidenceType._value2member_map_ else EvidenceType.METRIC,
                            name=ev.get("name", "unknown"),
                            value=ev.get("value", 0),
                            service=ev.get("service", service),
                            description=ev.get("description"),
                            timestamp=ts_str,
                        )
                    )
                consumption.evidence_items += 1

        # 2. Query Prometheus Metrics
        if consumption.tool_calls < budget.max_tool_calls and len(evidence_items) < budget.max_evidence_items:
            prom_queries = [
                (
                    f"rate(http_requests_total{{service='{service}', status=~'5..' }}[5m])",
                    "HTTP 5xx Error Rate",
                ),
                (
                    f"db_connection_pool_active{{service='{service}'}}",
                    "DB Connection Pool Active Connections",
                ),
                (
                    f"histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service='{service}'}}[5m]))",
                    "HTTP Request Latency p95",
                ),
            ]
            if is_slow_query_incident:
                prom_queries.append(
                    (f"slow_queries_total{{service='{service}'}}", "Slow Query Count")
                )

            for query_str, desc in prom_queries:
                if consumption.tool_calls >= budget.max_tool_calls or len(evidence_items) >= budget.max_evidence_items:
                    break

                consumption.tool_calls += 1
                try:
                    inp = PrometheusInstantQueryInput(query=query_str)
                    prom_res = self.prometheus.query_instant(inp)

                    tool_executions.append({
                        "tool": "PrometheusTool",
                        "query": query_str,
                        "status": prom_res.status.value,
                        "duration_ms": prom_res.execution_time_ms,
                        "error": prom_res.error_message,
                    })

                    if prom_res.status == EvidenceStatus.SUCCESS and prom_res.series:
                        for s in prom_res.series[:5]:  # Bounded to top 5 series
                            val = s.values[0].value if s.values else 0.0
                            # Prometheus histogram_quantile can return NaN when a
                            # bucket has no observations. It is not evidence and
                            # cannot be stored in PostgreSQL JSON columns.
                            if not math.isfinite(val):
                                continue
                            ts = (
                                datetime.fromtimestamp(s.values[0].timestamp, tz=timezone.utc).isoformat()
                                if s.values
                                else now_utc
                            )
                            evidence_items.append(
                                EvidenceItem(
                                    source=EvidenceType.METRIC,
                                    name=f"prometheus:{desc}",
                                    value=val,
                                    service=service,
                                    description=f"{desc}: {val}",
                                    timestamp=ts,
                                )
                            )
                            consumption.evidence_items += 1
                    elif prom_res.status == EvidenceStatus.EMPTY:
                        # Distinguish confirmed absence
                        evidence_items.append(
                            EvidenceItem(
                                source=EvidenceType.METRIC,
                                name=f"prometheus:{desc}",
                                value=0.0,
                                service=service,
                                description=f"Confirmed no matching metric series for {desc}",
                                timestamp=now_utc,
                            )
                        )
                        consumption.evidence_items += 1

                except Exception as exc:
                    logger.warning("Prometheus query '%s' failed: %s", query_str, exc)
                    tool_executions.append({
                        "tool": "PrometheusTool",
                        "query": query_str,
                        "status": "ERROR",
                        "error": str(exc),
                    })

        # 3. Query Loki Logs
        if consumption.tool_calls < budget.max_tool_calls and len(evidence_items) < budget.max_evidence_items:
            # Loki's `|=` filter is case-sensitive; Orders emits this warning
            # with an initial capital letter.
            log_signal = "Slow query" if is_slow_query_incident else "error"
            log_query = f'{{service="{service}"}} |= "{log_signal}" | json'
            consumption.tool_calls += 1
            try:
                loki_inp = LokiQueryInput(query=log_query, limit=10)
                loki_res = self.loki.query_logs(loki_inp)

                tool_executions.append({
                    "tool": "LokiTool",
                    "query": log_query,
                    "status": loki_res.status.value,
                    "duration_ms": loki_res.execution_time_ms,
                    "error": loki_res.error_message,
                })

                if loki_res.status == EvidenceStatus.SUCCESS and loki_res.streams:
                    raw_lines: List[str] = []
                    for stream in loki_res.streams:
                        for entry in stream.entries[:5]:
                            raw_lines.append(entry.line)
                            clean_line = sanitize_untrusted_evidence_text(entry.line)
                            evidence_items.append(
                                EvidenceItem(
                                    source=EvidenceType.LOG,
                                    name=f"log:{service}",
                                    value=clean_line,
                                    service=service,
                                    description=f"Log: {clean_line[:120]}",
                                    timestamp=now_utc,
                                )
                            )
                            consumption.evidence_items += 1
                            if len(evidence_items) >= budget.max_evidence_items:
                                break

                    # Generate bounded summary if multiple log lines exist
                    if len(raw_lines) >= 2 and len(evidence_items) < budget.max_evidence_items:
                        log_summary = summarize_logs(raw_lines, max_summary_chars=400)
                        evidence_items.append(
                            EvidenceItem(
                                source=EvidenceType.LOG,
                                name=f"log_summary:{service}",
                                value=log_summary,
                                service=service,
                                description="Bounded signature summary of observed error logs",
                                timestamp=now_utc,
                            )
                        )
                        consumption.evidence_items += 1

            except Exception as exc:
                logger.warning("Loki log collection failed: %s", exc)
                tool_executions.append({
                    "tool": "LokiTool",
                    "query": log_query,
                    "status": "ERROR",
                    "error": str(exc),
                })

        # 4. Query Jaeger Traces
        if consumption.tool_calls < budget.max_tool_calls and len(evidence_items) < budget.max_evidence_items:
            consumption.tool_calls += 1
            try:
                jaeger_inp = JaegerSearchTracesInput(
                    service=service,
                    tags=None if is_slow_query_incident else "error=true",
                    min_duration="300ms" if is_slow_query_incident else None,
                    limit=5,
                )
                jaeger_res = self.jaeger.search_traces(jaeger_inp)

                tool_executions.append({
                    "tool": "JaegerTool",
                    "query": (
                        f"service={service} minDuration=300ms"
                        if is_slow_query_incident
                        else f"service={service} tags.error=true"
                    ),
                    "status": jaeger_res.status.value,
                    "duration_ms": jaeger_res.execution_time_ms,
                    "error": jaeger_res.error_message,
                })

                if jaeger_res.status == EvidenceStatus.SUCCESS and jaeger_res.traces:
                    for trace in jaeger_res.traces:
                        duration_ms = trace.duration_us / 1000.0
                        evidence_items.append(
                            EvidenceItem(
                                source=EvidenceType.TRACE,
                                name=f"trace:{trace.trace_id}",
                                value=f"Duration: {duration_ms:.1f}ms, errors: {trace.error_count}",
                                service=service,
                                description=f"Span '{trace.root_operation or 'root'}' failure",
                                timestamp=now_utc,
                            )
                        )
                        consumption.evidence_items += 1
                        if len(evidence_items) >= budget.max_evidence_items:
                            break

            except Exception as exc:
                logger.warning("Jaeger trace collection failed: %s", exc)
                tool_executions.append({
                    "tool": "JaegerTool",
                    "query": f"service={service}",
                    "status": "ERROR",
                    "error": str(exc),
                })

        # 5. Query Git History & Recent Commits
        if consumption.tool_calls < budget.max_tool_calls and len(evidence_items) < budget.max_evidence_items:
            consumption.tool_calls += 1
            try:
                git_inp = GitLogInput(max_count=3)
                git_res = self.git.get_commits(git_inp)

                tool_executions.append({
                    "tool": "GitTool",
                    "query": "git log -n 3",
                    "status": git_res.status.value,
                    "duration_ms": git_res.execution_time_ms,
                    "error": git_res.error_message,
                })

                if git_res.status == EvidenceStatus.SUCCESS and git_res.commits:
                    for commit in git_res.commits:
                        clean_msg = sanitize_untrusted_evidence_text(commit.subject)
                        evidence_items.append(
                            EvidenceItem(
                                source=EvidenceType.CONFIG,
                                name=f"git_commit:{commit.short_hash}",
                                value=clean_msg,
                                service=service,
                                description=f"Commit by {commit.author_name}: {clean_msg}",
                                timestamp=commit.authored_date,
                            )
                        )
                        consumption.evidence_items += 1
                        if len(evidence_items) >= budget.max_evidence_items:
                            break

            except Exception as exc:
                logger.warning("Git inspection failed: %s", exc)
                tool_executions.append({
                    "tool": "GitTool",
                    "query": "git log",
                    "status": "ERROR",
                    "error": str(exc),
                })

        return evidence_items, tool_executions
