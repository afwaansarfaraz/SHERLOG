"""Sherlog Investigation Pipeline package.

Exports state machine states, execution schemas, orchestrator pipeline,
evaluator, generator, and evidence collector.
"""

from backend.app.investigation.evaluator import DeterministicEvaluator
from backend.app.investigation.evidence import EvidenceCollector, sanitize_untrusted_evidence_text
from backend.app.investigation.generator import HypothesisGenerator
from backend.app.investigation.orchestrator import InvestigationPipeline
from backend.app.investigation.rag import KnowledgeRetriever, RAGRetrievalResult
from backend.app.investigation.schemas import (
    BudgetConsumption,
    ExecutionBudget,
    HypothesisGenerationOutput,
    HypothesisProposal,
    InvestigationResult,
)
from backend.app.investigation.states import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    InvalidStateTransitionError,
    InvestigationState,
    is_valid_transition,
    validate_transition,
)

__all__ = [
    "InvestigationState",
    "TERMINAL_STATES",
    "VALID_TRANSITIONS",
    "InvalidStateTransitionError",
    "is_valid_transition",
    "validate_transition",
    "ExecutionBudget",
    "BudgetConsumption",
    "HypothesisProposal",
    "HypothesisGenerationOutput",
    "InvestigationResult",
    "EvidenceCollector",
    "sanitize_untrusted_evidence_text",
    "HypothesisGenerator",
    "DeterministicEvaluator",
    "KnowledgeRetriever",
    "RAGRetrievalResult",
    "InvestigationPipeline",
]
