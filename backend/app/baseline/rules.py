"""Deterministic rules for baseline incident root-cause diagnosis.

Every rule evaluates concrete observable signals without calling an LLM,
never invents evidence, and cites verifiable signals in its diagnosis.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.baseline.models import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceType,
    HypothesisRanking,
    RootCause,
)


class BaseRule:
    """Base class for deterministic diagnosis rules."""

    rule_name: str
    root_cause: str
    title: str
    recommended_remediation: str

    def evaluate(
        self,
        incident_data: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> Optional[HypothesisRanking]:
        """Evaluate evidence against rule criteria and return hypothesis if signals match."""
        raise NotImplementedError


class DbPoolExhaustionRule(BaseRule):
    """Diagnoses database connection pool exhaustion from metrics, logs, and alerts."""

    rule_name = "RULE_DB_POOL_EXHAUSTION"
    root_cause = RootCause.DATABASE_CONNECTION_POOL_EXHAUSTION.value
    title = "Database Connection Pool Exhaustion"
    recommended_remediation = "increase_db_connection_pool_size"

    def evaluate(
        self,
        incident_data: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> Optional[HypothesisRanking]:
        score = 0.0
        supporting: List[str] = []
        matched_rules = [self.rule_name]

        # 1. Inspect alerts in incident metadata
        meta = incident_data.get("metadata") or {}
        alertname = str(meta.get("alertname", "")).lower()
        if "pool" in alertname or alertname == "dbpoolexhausted":
            score += 40.0
            supporting.append(f"Alert fired: '{meta.get('alertname')}'")

        summary_text = str(incident_data.get("summary", "")).lower()
        title_text = str(incident_data.get("title", "")).lower()
        if "connection pool" in summary_text or "connection pool" in title_text or "pool exhaustion" in summary_text:
            score += 20.0
            supporting.append("Incident description identifies connection pool saturation")

        # 2. Inspect telemetry evidence items
        for item in evidence:
            name_lower = item.name.lower()
            val_str = str(item.value).lower()

            # Primary metric: db_pool_exhaustion_errors_total > 0
            if "pool_exhaustion" in name_lower and item.source in (EvidenceType.METRIC, "metric"):
                try:
                    num_val = float(item.value)
                    if num_val > 0:
                        score += 50.0
                        supporting.append(f"Metric '{item.name}' elevated at {num_val}")
                except (ValueError, TypeError):
                    pass

            # Primary metric: db_connections_active at pool ceiling
            if "connections_active" in name_lower and item.source in (EvidenceType.METRIC, "metric"):
                try:
                    if float(item.value) >= 20.0:
                        score += 30.0
                        supporting.append(f"Active DB connections saturated at {item.value}")
                except (ValueError, TypeError):
                    pass

            # Primary log signatures
            if item.source in (EvidenceType.LOG, "log"):
                if any(k in val_str for k in [
                    "connection pool exhausted",
                    "timeout waiting for connection",
                    "queuepool limit of size",
                    "checking out all pool connections",
                    "connection checkout timeout",
                ]):
                    score += 40.0
                    supporting.append(f"Log matches pool exhaustion signature: \"{item.value[:80]}\"")

        if score <= 0.0:
            return None

        confidence = (
            ConfidenceLevel.HIGH if score >= 70.0
            else ConfidenceLevel.MEDIUM if score >= 40.0
            else ConfidenceLevel.LOW
        )

        return HypothesisRanking(
            root_cause=self.root_cause,
            title=self.title,
            score=score,
            confidence=confidence,
            matched_rules=matched_rules,
            supporting_evidence=supporting,
            recommended_remediation=self.recommended_remediation,
        )


class SlowQueryRule(BaseRule):
    """Diagnoses slow database queries from latency metrics, slow query counters, and logs."""

    rule_name = "RULE_SLOW_QUERY"
    root_cause = RootCause.SLOW_DATABASE_QUERY.value
    title = "Slow Database Query Latency"
    recommended_remediation = "optimize_query_or_add_index"

    def evaluate(
        self,
        incident_data: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> Optional[HypothesisRanking]:
        score = 0.0
        supporting: List[str] = []
        matched_rules = [self.rule_name]

        meta = incident_data.get("metadata") or {}
        alertname = str(meta.get("alertname", "")).lower()
        if "slowquery" in alertname or alertname == "slowquerydetected":
            score += 40.0
            supporting.append(f"Alert fired: '{meta.get('alertname')}'")

        summary_text = str(incident_data.get("summary", "")).lower()
        title_text = str(incident_data.get("title", "")).lower()
        if "slow query" in summary_text or "slow query" in title_text:
            score += 20.0
            supporting.append("Incident description identifies slow database query pattern")

        for item in evidence:
            name_lower = item.name.lower()
            val_str = str(item.value).lower()

            # Metric: slow_queries_total > 0
            if "slow_quer" in name_lower and item.source in (EvidenceType.METRIC, "metric"):
                try:
                    num_val = float(item.value)
                    if num_val > 0:
                        score += 50.0
                        supporting.append(f"Metric '{item.name}' elevated at {num_val}")
                except (ValueError, TypeError):
                    pass

            # Metric: high P95 latency (latency > 1.0s)
            if ("latency" in name_lower or "duration" in name_lower) and item.source in (EvidenceType.METRIC, "metric"):
                try:
                    num_val = float(item.value)
                    if num_val >= 1.0:
                        score += 30.0
                        supporting.append(f"High P95 latency detected: {num_val:.2f}s")
                except (ValueError, TypeError):
                    pass

            # Log signatures
            if item.source in (EvidenceType.LOG, "log"):
                if any(k in val_str for k in [
                    "slow query fault active",
                    "pg_sleep",
                    "heavy db query",
                    "executing heavy db query",
                    "query execution exceeded threshold",
                ]):
                    score += 40.0
                    supporting.append(f"Log matches slow query signature: \"{item.value[:80]}\"")

        if score <= 0.0:
            return None

        confidence = (
            ConfidenceLevel.HIGH if score >= 70.0
            else ConfidenceLevel.MEDIUM if score >= 40.0
            else ConfidenceLevel.LOW
        )

        return HypothesisRanking(
            root_cause=self.root_cause,
            title=self.title,
            score=score,
            confidence=confidence,
            matched_rules=matched_rules,
            supporting_evidence=supporting,
            recommended_remediation=self.recommended_remediation,
        )


class DependencyTimeoutRule(BaseRule):
    """Diagnoses downstream HTTP dependency timeouts (e.g. payments timeout from orders)."""

    rule_name = "RULE_DEPENDENCY_TIMEOUT"
    root_cause = RootCause.DOWNSTREAM_DEPENDENCY_TIMEOUT.value
    title = "Downstream Dependency Timeout"
    recommended_remediation = "increase_downstream_timeout"

    def evaluate(
        self,
        incident_data: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> Optional[HypothesisRanking]:
        score = 0.0
        supporting: List[str] = []
        matched_rules = [self.rule_name]

        meta = incident_data.get("metadata") or {}
        alertname = str(meta.get("alertname", "")).lower()
        if "dependencytimeout" in alertname or ("timeout" in alertname and "dependency" in alertname):
            score += 40.0
            supporting.append(f"Alert fired: '{meta.get('alertname')}'")

        summary_text = str(incident_data.get("summary", "")).lower()
        title_text = str(incident_data.get("title", "")).lower()
        if "dependency timeout" in summary_text or "gateway timeout" in summary_text or "payment service timed out" in summary_text:
            score += 20.0
            supporting.append("Incident description cites downstream dependency timeout")

        for item in evidence:
            name_lower = item.name.lower()
            val_str = str(item.value).lower()

            # Metric: dependency_timeouts_total > 0
            if "dependency_timeout" in name_lower and item.source in (EvidenceType.METRIC, "metric"):
                try:
                    num_val = float(item.value)
                    if num_val > 0:
                        score += 50.0
                        supporting.append(f"Metric '{item.name}' elevated at {num_val}")
                except (ValueError, TypeError):
                    pass

            # Trace / HTTP status 504 Gateway Timeout
            if ("status_code" in name_lower or "http_status" in name_lower or item.source in (EvidenceType.TRACE, "trace")):
                if "504" in val_str or item.value == 504:
                    score += 35.0
                    supporting.append("Trace span returned HTTP 504 Gateway Timeout")

            # Log signatures
            if item.source in (EvidenceType.LOG, "log"):
                if any(k in val_str for k in [
                    "downstream dependency timeout",
                    "payment service timed out",
                    "timed out attempting to communicate with payments",
                    "timeout calling payments service",
                    "payment_timeout",
                ]):
                    score += 40.0
                    supporting.append(f"Log matches dependency timeout signature: \"{item.value[:80]}\"")

        if score <= 0.0:
            return None

        confidence = (
            ConfidenceLevel.HIGH if score >= 70.0
            else ConfidenceLevel.MEDIUM if score >= 40.0
            else ConfidenceLevel.LOW
        )

        return HypothesisRanking(
            root_cause=self.root_cause,
            title=self.title,
            score=score,
            confidence=confidence,
            matched_rules=matched_rules,
            supporting_evidence=supporting,
            recommended_remediation=self.recommended_remediation,
        )


class TrafficSpikeRule(BaseRule):
    """Diagnoses sudden load and concurrency surges on API endpoints."""

    rule_name = "RULE_TRAFFIC_SPIKE"
    root_cause = RootCause.SUDDEN_TRAFFIC_SPIKE.value
    title = "Sudden Traffic Spike"
    recommended_remediation = "apply_rate_limiting_and_scale"

    def evaluate(
        self,
        incident_data: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> Optional[HypothesisRanking]:
        score = 0.0
        supporting: List[str] = []
        matched_rules = [self.rule_name]

        meta = incident_data.get("metadata") or {}
        alertname = str(meta.get("alertname", "")).lower()
        if "traffic" in alertname or "spike" in alertname:
            score += 40.0
            supporting.append(f"Alert fired: '{meta.get('alertname')}'")

        summary_text = str(incident_data.get("summary", "")).lower()
        title_text = str(incident_data.get("title", "")).lower()
        if "traffic spike" in summary_text or "traffic spike" in title_text or "high concurrency" in summary_text:
            score += 20.0
            supporting.append("Incident description cites sudden traffic surge")

        for item in evidence:
            name_lower = item.name.lower()
            val_str = str(item.value).lower()

            # Metric: requests rate / concurrency spike
            if any(k in name_lower for k in ["request_rate", "requests_per_second", "traffic_concurrency", "http_requests_total"]):
                try:
                    num_val = float(item.value)
                    if num_val >= 50.0:
                        score += 45.0
                        supporting.append(f"High request volume metric '{item.name}': {num_val}/s")
                except (ValueError, TypeError):
                    pass

            # Log signatures
            if item.source in (EvidenceType.LOG, "log"):
                if any(k in val_str for k in [
                    "sudden traffic spike",
                    "high concurrency load",
                    "traffic volume exceeding capacity",
                    "concurrency limit reached",
                    "spike request exception",
                    "rate limit exceeded",
                ]):
                    score += 40.0
                    supporting.append(f"Log matches traffic surge signature: \"{item.value[:80]}\"")

        if score <= 0.0:
            return None

        confidence = (
            ConfidenceLevel.HIGH if score >= 70.0
            else ConfidenceLevel.MEDIUM if score >= 40.0
            else ConfidenceLevel.LOW
        )

        return HypothesisRanking(
            root_cause=self.root_cause,
            title=self.title,
            score=score,
            confidence=confidence,
            matched_rules=matched_rules,
            supporting_evidence=supporting,
            recommended_remediation=self.recommended_remediation,
        )


class ConfigurationErrorRule(BaseRule):
    """Diagnoses service endpoint and downstream address misconfigurations (HTTP 502 / connection refused)."""

    rule_name = "RULE_CONFIGURATION_ERROR"
    root_cause = RootCause.INVALID_SERVICE_CONFIGURATION.value
    title = "Invalid Service Configuration"
    recommended_remediation = "revert_configuration_change"

    def evaluate(
        self,
        incident_data: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> Optional[HypothesisRanking]:
        score = 0.0
        supporting: List[str] = []
        matched_rules = [self.rule_name]

        meta = incident_data.get("metadata") or {}
        alertname = str(meta.get("alertname", "")).lower()
        if "config" in alertname:
            score += 40.0
            supporting.append(f"Alert fired: '{meta.get('alertname')}'")

        summary_text = str(incident_data.get("summary", "")).lower()
        title_text = str(incident_data.get("title", "")).lower()
        if "configuration error" in summary_text or "misconfiguration" in summary_text or "invalid downstream" in summary_text:
            score += 20.0
            supporting.append("Incident description cites configuration failure")

        for item in evidence:
            name_lower = item.name.lower()
            val_str = str(item.value).lower()

            # HTTP 502 Bad Gateway / Connection Error (NOT a timeout)
            if ("status_code" in name_lower or "http_status" in name_lower or item.source in (EvidenceType.TRACE, "trace")):
                if "502" in val_str or item.value == 502:
                    score += 40.0
                    supporting.append("Trace span returned HTTP 502 Bad Gateway (connection setup failure)")

            # Config diff or invalid URL evidence
            if item.source in (EvidenceType.CONFIG, "config") or "service_url" in name_lower:
                if any(k in val_str for k in ["invalid", "bad_host", "localhost:9999", "wrong_port", "unreachable"]):
                    score += 50.0
                    supporting.append(f"Configuration diff indicates invalid URL setting: {item.value}")

            # Log signatures
            if item.source in (EvidenceType.LOG, "log"):
                if any(k in val_str for k in [
                    "downstream connection error",
                    "failed to communicate with payment gateway",
                    "connection refused",
                    "connecterror",
                    "configuration_error updated",
                    "injected an invalid downstream service configuration",
                ]):
                    score += 40.0
                    supporting.append(f"Log matches configuration error signature: \"{item.value[:80]}\"")

        if score <= 0.0:
            return None

        confidence = (
            ConfidenceLevel.HIGH if score >= 70.0
            else ConfidenceLevel.MEDIUM if score >= 40.0
            else ConfidenceLevel.LOW
        )

        return HypothesisRanking(
            root_cause=self.root_cause,
            title=self.title,
            score=score,
            confidence=confidence,
            matched_rules=matched_rules,
            supporting_evidence=supporting,
            recommended_remediation=self.recommended_remediation,
        )


class MemoryLeakRule(BaseRule):
    """Diagnoses memory leaks and RSS heap exhaustion."""

    rule_name = "RULE_MEMORY_LEAK"
    root_cause = RootCause.MEMORY_LEAK_EXHAUSTION.value
    title = "Memory Leak & Heap Exhaustion"
    recommended_remediation = "restart_service_and_inspect_heap"

    def evaluate(
        self,
        incident_data: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> Optional[HypothesisRanking]:
        score = 0.0
        supporting: List[str] = []
        matched_rules = [self.rule_name]

        meta = incident_data.get("metadata") or {}
        alertname = str(meta.get("alertname", "")).lower()
        if "memory" in alertname or "oom" in alertname:
            score += 40.0
            supporting.append(f"Alert fired: '{meta.get('alertname')}'")

        summary_text = str(incident_data.get("summary", "")).lower()
        title_text = str(incident_data.get("title", "")).lower()
        if "memory leak" in summary_text or "rss usage" in summary_text or "oom" in summary_text:
            score += 20.0
            supporting.append("Incident description cites memory consumption growth")

        for item in evidence:
            name_lower = item.name.lower()
            val_str = str(item.value).lower()

            # Metric: memory usage > 90% or strictly ascending
            if any(k in name_lower for k in ["memory_rss_bytes", "process_resident_memory_bytes", "memory_usage_ratio"]):
                try:
                    num_val = float(item.value)
                    if num_val >= 0.85:
                        score += 50.0
                        supporting.append(f"Memory metric '{item.name}' elevated above threshold: {num_val}")
                except (ValueError, TypeError):
                    pass

            # Exit code 137 / OOMKill
            if "exit_code" in name_lower and ("137" in val_str or item.value == 137):
                score += 50.0
                supporting.append("Process terminated with exit code 137 (OOMKilled)")

            # Log signatures
            if item.source in (EvidenceType.LOG, "log"):
                if any(k in val_str for k in [
                    "oomkilled",
                    "out of memory",
                    "rss memory consumption leak",
                    "heap exhausted",
                    "memory ceiling exceeded",
                ]):
                    score += 40.0
                    supporting.append(f"Log matches memory exhaustion signature: \"{item.value[:80]}\"")

        if score <= 0.0:
            return None

        confidence = (
            ConfidenceLevel.HIGH if score >= 70.0
            else ConfidenceLevel.MEDIUM if score >= 40.0
            else ConfidenceLevel.LOW
        )

        return HypothesisRanking(
            root_cause=self.root_cause,
            title=self.title,
            score=score,
            confidence=confidence,
            matched_rules=matched_rules,
            supporting_evidence=supporting,
            recommended_remediation=self.recommended_remediation,
        )


ALL_RULES: List[BaseRule] = [
    DbPoolExhaustionRule(),
    SlowQueryRule(),
    DependencyTimeoutRule(),
    TrafficSpikeRule(),
    ConfigurationErrorRule(),
    MemoryLeakRule(),
]
