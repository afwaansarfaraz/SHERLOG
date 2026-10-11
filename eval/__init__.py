"""Sherlog Evaluation Framework.

Provides benchmark scenario loaders, evaluation metrics, and runners for comparing
deterministic baselines and AI incident investigation agents.
"""

from eval.models import (
    BenchmarkScenario,
    EvaluationRunReport,
    ScenarioEvaluationResult,
)
from eval.loader import load_scenarios
from eval.runner import EvaluationRunner

__all__ = [
    "BenchmarkScenario",
    "EvaluationRunReport",
    "EvaluationRunner",
    "ScenarioEvaluationResult",
    "load_scenarios",
]
