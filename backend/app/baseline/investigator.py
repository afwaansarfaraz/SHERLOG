"""Deterministic Rule-Based Incident Investigator for Sherlog.

Applies explicit, transparent rules against incidents and observability evidence
to rank likely root causes without calling an LLM.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from backend.app.baseline.models import (
    ConfidenceLevel,
    EvidenceItem,
    HypothesisRanking,
    InvestigationReport,
)
from backend.app.baseline.rules import ALL_RULES, BaseRule


class RuleBasedInvestigator:
    """Deterministic, rule-based incident investigator.

    Evaluates observable metrics, log lines, traces, and alert metadata against
    explicit rules to produce explainable root-cause rankings with evidence references.
    """

    def __init__(self, rules: Optional[List[BaseRule]] = None, min_score_threshold: float = 30.0):
        self.rules = rules if rules is not None else ALL_RULES
        self.min_score_threshold = min_score_threshold

    def investigate(
        self,
        incident: Union[Dict[str, Any], BaseModel],
        evidence: Optional[List[EvidenceItem]] = None,
    ) -> InvestigationReport:
        """Execute deterministic rule evaluation against the incident and evidence.

        Args:
            incident: Incident dict or Pydantic model containing title, service, summary, metadata, etc.
            evidence: List of EvidenceItem instances collected from observability systems.

        Returns:
            Structured InvestigationReport with ranked root causes, confidence, and explanations.
        """
        # Convert Pydantic models to dict if needed
        if isinstance(incident, BaseModel):
            incident_data = incident.model_dump()
        else:
            incident_data = dict(incident)

        evidence_items = evidence or []
        incident_id = incident_data.get("id")
        service = incident_data.get("service", "unknown")

        # Evaluate each rule deterministically
        ranked: List[HypothesisRanking] = []
        rules_matched = 0

        for rule in self.rules:
            candidate = rule.evaluate(incident_data, evidence_items)
            if candidate is not None:
                rules_matched += 1
                ranked.append(candidate)

        # Sort descending by deterministic score
        ranked.sort(key=lambda h: h.score, reverse=True)

        # Check sufficiency: must meet min score threshold
        has_sufficient = False
        top_root_cause: Optional[HypothesisRanking] = None

        if ranked and ranked[0].score >= self.min_score_threshold:
            has_sufficient = True
            top_root_cause = ranked[0]
            summary = (
                f"Diagnosed leading root cause as '{top_root_cause.title}' "
                f"with {top_root_cause.confidence.value} confidence (score: {top_root_cause.score:.1f}). "
                f"Backed by {len(top_root_cause.supporting_evidence)} corroborating evidence signals: "
                f"{'; '.join(top_root_cause.supporting_evidence[:3])}."
            )
        elif ranked:
            # Low signals exist but not enough to meet threshold
            summary = (
                "Ambiguous or weak observability signals detected. "
                "Evidence is insufficient to conclude a root cause with acceptable certainty."
            )
        else:
            summary = (
                "No matching observability evidence patterns found. "
                "Insufficient evidence to determine root cause."
            )

        return InvestigationReport(
            incident_id=incident_id,
            service=service,
            has_sufficient_evidence=has_sufficient,
            top_root_cause=top_root_cause,
            ranked_root_causes=ranked,
            evidence_count=len(evidence_items),
            rules_evaluated=len(self.rules),
            rules_matched=rules_matched,
            summary=summary,
        )
