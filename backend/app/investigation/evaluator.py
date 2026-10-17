"""Deterministic Evidence Evaluator scoring root cause hypotheses against concrete telemetry."""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.baseline.investigator import RuleBasedInvestigator
from backend.app.baseline.models import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceType,
    HypothesisRanking,
    InvestigationReport,
)
from backend.app.investigation.schemas import HypothesisProposal

logger = logging.getLogger(__name__)

# Weight mapping for evidence signal categories
_SIGNAL_WEIGHTS = {
    EvidenceType.METRIC: 30.0,
    EvidenceType.LOG: 25.0,
    EvidenceType.TRACE: 20.0,
    EvidenceType.CONFIG: 20.0,
    EvidenceType.ALERT: 10.0,
}

_CONTRADICTING_PENALTY = 25.0


class DeterministicEvaluator:
    """Scores hypotheses deterministically against concrete evidence without trusting LLM self-confidence."""

    def __init__(self, min_score_threshold: float = 30.0):
        self.min_score_threshold = min_score_threshold
        self.baseline_investigator = RuleBasedInvestigator(min_score_threshold=min_score_threshold)

    def evaluate_hypotheses(
        self,
        hypotheses: List[HypothesisProposal],
        evidence: List[EvidenceItem],
    ) -> Tuple[List[HypothesisRanking], bool, Optional[HypothesisRanking], str]:
        """Score and rank candidate hypotheses against collected evidence.
        
        Returns:
            Tuple of:
            - Ranked list of HypothesisRanking sorted descending by score.
            - Boolean has_sufficient_evidence.
            - Top HypothesisRanking (or None if insufficient).
            - Explanatory rationale string.
        """
        if not hypotheses:
            return [], False, None, "No hypotheses provided for evaluation."

        ranked: List[HypothesisRanking] = []

        for hypo in hypotheses:
            ranking = self._score_single_hypothesis(hypo, evidence)
            ranked.append(ranking)

        # Sort strictly descending by deterministic score
        ranked.sort(key=lambda h: h.score, reverse=True)

        # Check sufficiency threshold
        if ranked and ranked[0].score >= self.min_score_threshold:
            top_cause = ranked[0]
            rationale = (
                f"Leading root cause deterministically verified as '{top_cause.title}' "
                f"with score {top_cause.score:.1f} ({top_cause.confidence.value}). "
                f"Corroborated by {len(top_cause.supporting_evidence)} distinct evidence signals."
            )
            return ranked, True, top_cause, rationale
        elif ranked:
            top_cause = ranked[0]
            rationale = (
                f"Leading hypothesis '{top_cause.title}' scored {top_cause.score:.1f}, "
                f"which falls below the required threshold of {self.min_score_threshold:.1f}. "
                "Evidence is insufficient to conclude root cause."
            )
            return ranked, False, None, rationale
        else:
            return [], False, None, "Insufficient evidence to determine root cause."

    def _score_single_hypothesis(
        self,
        hypo: HypothesisProposal,
        evidence: List[EvidenceItem],
    ) -> HypothesisRanking:
        """Compute deterministic score for a single proposed hypothesis based on verified evidence signals."""
        matched_evidence_keys: Set[str] = set()
        matched_evidence_labels: List[str] = []
        contradicting_evidence_keys: Set[str] = set()
        score = 0.0

        # Keywords relevant to the proposed root cause
        hypo_text = f"{hypo.root_cause} {hypo.title} {hypo.causal_explanation}".lower()

        for item in evidence:
            item_desc = f"{item.source.value.upper()}: {item.name}".lower()
            val_str = str(item.value).lower()
            combined_item_text = f"{item_desc} {val_str}"

            # Check if evidence corroborates hypothesis
            is_corroborating = False
            for ref in hypo.supporting_evidence_refs:
                ref_clean = ref.lower().strip()
                if ref_clean and (ref_clean in combined_item_text or item.name.lower() in ref_clean):
                    is_corroborating = True
                    break

            # Keyword heuristic match for fault correlation
            if not is_corroborating:
                if "pool" in hypo_text and "pool" in combined_item_text:
                    is_corroborating = True
                elif "timeout" in hypo_text and ("timeout" in combined_item_text or "504" in combined_item_text):
                    is_corroborating = True
                elif "slow" in hypo_text and ("latency" in combined_item_text or "duration" in combined_item_text):
                    is_corroborating = True
                elif "traffic" in hypo_text and ("rate" in combined_item_text or "spike" in combined_item_text):
                    is_corroborating = True
                elif "config" in hypo_text and ("config" in combined_item_text or "commit" in combined_item_text):
                    is_corroborating = True

            # Check for explicit contradictions
            is_contradicting = False
            for ref in hypo.contradicting_evidence_refs:
                ref_clean = ref.lower().strip()
                if ref_clean and (ref_clean in combined_item_text or item.name.lower() in ref_clean):
                    is_contradicting = True
                    break

            item_key = f"{item.source.value}:{item.name}"
            if is_corroborating and item_key not in matched_evidence_keys:
                weight = _SIGNAL_WEIGHTS.get(item.source, 15.0)
                score += weight
                matched_evidence_keys.add(item_key)
                matched_evidence_labels.append(f"{item.source.value.upper()}: {item.name} ({str(item.value)[:60]})")

            if is_contradicting and item_key not in contradicting_evidence_keys:
                score -= _CONTRADICTING_PENALTY
                contradicting_evidence_keys.add(item_key)

        # Clamp score between 0.0 and 100.0
        final_score = max(0.0, min(100.0, score))

        # Categorize confidence strictly from deterministic score
        if final_score >= 70.0:
            confidence = ConfidenceLevel.HIGH
        elif final_score >= 50.0:
            confidence = ConfidenceLevel.MEDIUM
        elif final_score >= self.min_score_threshold:
            confidence = ConfidenceLevel.LOW
        else:
            confidence = ConfidenceLevel.INSUFFICIENT_EVIDENCE

        return HypothesisRanking(
            root_cause=hypo.root_cause,
            title=hypo.title,
            score=final_score,
            confidence=confidence,
            matched_rules=[f"evidence_match_{hypo.root_cause}"],
            supporting_evidence=sorted(matched_evidence_labels),
            recommended_remediation=None,
        )

    def evaluate_with_baseline_fallback(
        self,
        incident: Dict[str, Any],
        evidence: List[EvidenceItem],
    ) -> InvestigationReport:
        """Execute deterministic rule-based baseline as a verified fallback when LLM fails."""
        return self.baseline_investigator.investigate(incident=incident, evidence=evidence)
