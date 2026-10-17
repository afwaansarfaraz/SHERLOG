"""State machine states, valid transitions, and transition validators for Sherlog investigations."""

from enum import Enum
from typing import Dict, Set


class InvestigationState(str, Enum):
    """Explicit lifecycle states for an AI incident investigation."""

    QUEUED = "QUEUED"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    GENERATING_HYPOTHESES = "GENERATING_HYPOTHESES"
    EVALUATING_HYPOTHESES = "EVALUATING_HYPOTHESES"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"


# Explicit terminal states where execution stops and cannot transition further
TERMINAL_STATES: Set[InvestigationState] = {
    InvestigationState.COMPLETED,
    InvestigationState.INSUFFICIENT_EVIDENCE,
    InvestigationState.FAILED,
}

# Central transition matrix mapping source states to allowed target states
VALID_TRANSITIONS: Dict[InvestigationState, Set[InvestigationState]] = {
    InvestigationState.QUEUED: {
        InvestigationState.COLLECTING_EVIDENCE,
        InvestigationState.FAILED,
    },
    InvestigationState.COLLECTING_EVIDENCE: {
        InvestigationState.GENERATING_HYPOTHESES,
        InvestigationState.EVALUATING_HYPOTHESES,  # When falling back to baseline directly
        InvestigationState.INSUFFICIENT_EVIDENCE,
        InvestigationState.FAILED,
    },
    InvestigationState.GENERATING_HYPOTHESES: {
        InvestigationState.EVALUATING_HYPOTHESES,
        InvestigationState.FAILED,
    },
    InvestigationState.EVALUATING_HYPOTHESES: {
        InvestigationState.COMPLETED,
        InvestigationState.INSUFFICIENT_EVIDENCE,
        InvestigationState.FAILED,
    },
    # Terminal states have no outbound transitions
    InvestigationState.COMPLETED: set(),
    InvestigationState.INSUFFICIENT_EVIDENCE: set(),
    InvestigationState.FAILED: set(),
}


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state machine transition is attempted."""

    def __init__(self, from_state: InvestigationState, to_state: InvestigationState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid state transition attempted: '{from_state.value}' -> '{to_state.value}'. "
            f"Allowed target states from '{from_state.value}': {[s.value for s in VALID_TRANSITIONS.get(from_state, set())]}"
        )


def is_valid_transition(from_state: InvestigationState, to_state: InvestigationState) -> bool:
    """Return True if transitioning from_state to to_state is permissible."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def validate_transition(from_state: InvestigationState, to_state: InvestigationState) -> None:
    """Validate state transition, raising InvalidStateTransitionError if illegal."""
    if not is_valid_transition(from_state, to_state):
        raise InvalidStateTransitionError(from_state, to_state)
