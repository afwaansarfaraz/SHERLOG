"""Investigation Triage Router for Sherlog.

Provides fast, cheap incident classification and tool prioritization:
- Uses deterministic heuristics by default (0 extra LLM calls, 0 latency)
- Optionally routes through cheap/fast LLM if explicitly enabled in configuration
- Selects high-priority telemetry queries and relevant knowledge domain
"""

from enum import Enum
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.config import settings

logger = logging.getLogger(__name__)


class IncidentCategory(str, Enum):
    """Categorized domain of an incident."""
    DATABASE = "database"
    NETWORK_DEPENDENCY = "network_dependency"
    TRAFFIC_SATURATION = "traffic_saturation"
    CONFIGURATION = "configuration"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    GENERIC = "generic"


class RoutingDecision(BaseModel):
    """Triage decision determining targeted telemetry queries and runbook domains."""
    category: IncidentCategory
    recommended_tools: List[str] = Field(default_factory=list)
    search_keywords: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    router_source: str = "deterministic_rules"


class InvestigationRouter:
    """Configurable triage router directing investigations to high-signal telemetry."""

    def __init__(self, use_llm_router: bool = False):
        self.use_llm_router = use_llm_router

    def route_incident(self, incident: Dict[str, Any]) -> RoutingDecision:
        """Route incident to high-probability tool targets without extra LLM overhead.

        By default, uses deterministic pattern matching against title, summary,
        and alert metadata. Avoids unnecessary LLM calls.
        """
        title = (incident.get("title") or "").lower()
        summary = (incident.get("summary") or "").lower()
        service = (incident.get("service") or "").lower()
        text = f"{title} {summary}"

        # 1. Database connection / pool / query patterns
        if any(w in text for w in ("pool", "database", "postgres", "sql", "db_", "connection")):
            return RoutingDecision(
                category=IncidentCategory.DATABASE,
                recommended_tools=["PrometheusTool", "LokiTool", "KnowledgeRetriever"],
                search_keywords=["pool", "database", "postgres", "connection", "query"],
                confidence=0.95,
                router_source="deterministic_rules",
            )

        # 2. Downstream dependency timeout patterns
        if any(w in text for w in ("timeout", "gateway", "504", "502", "downstream", "dependency")):
            return RoutingDecision(
                category=IncidentCategory.NETWORK_DEPENDENCY,
                recommended_tools=["JaegerTool", "LokiTool", "KnowledgeRetriever"],
                search_keywords=["timeout", "downstream", "gateway", "dependency"],
                confidence=0.90,
                router_source="deterministic_rules",
            )

        # 3. Traffic spike patterns
        if any(w in text for w in ("traffic", "spike", "rate limit", "429", "requests_total")):
            return RoutingDecision(
                category=IncidentCategory.TRAFFIC_SATURATION,
                recommended_tools=["PrometheusTool", "KnowledgeRetriever"],
                search_keywords=["traffic", "spike", "rate", "requests"],
                confidence=0.85,
                router_source="deterministic_rules",
            )

        # 4. Configuration / deploy crash patterns
        if any(w in text for w in ("config", "crash", "missing env", "deploy", "startup")):
            return RoutingDecision(
                category=IncidentCategory.CONFIGURATION,
                recommended_tools=["GitTool", "LokiTool", "KnowledgeRetriever"],
                search_keywords=["config", "deployment", "env", "startup"],
                confidence=0.85,
                router_source="deterministic_rules",
            )

        # Default fallback
        return RoutingDecision(
            category=IncidentCategory.GENERIC,
            recommended_tools=["PrometheusTool", "LokiTool", "JaegerTool", "GitTool", "KnowledgeRetriever"],
            search_keywords=[service],
            confidence=0.70,
            router_source="deterministic_rules",
        )
