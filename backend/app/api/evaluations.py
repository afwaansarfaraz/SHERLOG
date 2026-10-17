"""Evaluations and Benchmark Suite API.

Provides endpoints to list benchmark scenarios, inspect historical runs,
trigger actual evaluation runs via the evaluation runner, and view comparative evaluation metrics.
Never returns fake scores or fabricated scenarios.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from eval.loader import get_default_scenarios_dir, load_scenarios
from eval.models import (
    BenchmarkScenario,
    EvaluationRunReport,
    ScenarioEvaluationResult,
)
from eval.runner import EvaluationRunner, get_default_results_dir

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory execution lock to prevent duplicate concurrent benchmark runs
_benchmark_lock = asyncio.Lock()
_is_running_benchmark = False


class ScenarioSummary(BaseModel):
    scenario_id: str
    name: str
    fault_id: str
    service: str
    description: str
    expected_root_cause: str
    expected_remediations: List[str] = []
    evidence_count: int
    expect_insufficient_evidence: bool = False


class RunSummary(BaseModel):
    run_id: str
    timestamp: str
    evaluator_name: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    top_1_accuracy: float
    top_3_accuracy: float
    avg_latency_ms: float


class BenchmarkTriggerRequest(BaseModel):
    evaluator_name: str = Field(
        default="Rule-Based Deterministic Baseline",
        description="Name of the evaluation configuration",
    )
    save_results: bool = Field(default=True, description="Whether to persist results to disk")


@router.get(
    "/scenarios",
    response_model=List[ScenarioSummary],
    summary="List all available ground-truth benchmark scenarios",
)
def list_scenarios() -> List[ScenarioSummary]:
    """Retrieve all ground-truth incident scenarios available in eval/scenarios."""
    try:
        scenarios = load_scenarios()
        return [
            ScenarioSummary(
                scenario_id=s.scenario_id,
                name=s.name,
                fault_id=s.fault_id,
                service=s.service,
                description=s.description,
                expected_root_cause=s.expected_root_cause,
                expected_remediations=s.expected_remediations,
                evidence_count=len(s.evidence),
                expect_insufficient_evidence=s.expect_insufficient_evidence,
            )
            for s in scenarios
        ]
    except Exception as exc:
        logger.error("Failed loading scenarios: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed loading evaluation scenarios: {exc}",
        )


@router.get(
    "/runs",
    response_model=List[RunSummary],
    summary="List all historical evaluation benchmark runs",
)
def list_runs() -> List[RunSummary]:
    """Retrieve historical benchmark runs from eval/results."""
    results_dir = get_default_results_dir()
    runs: List[RunSummary] = []

    if not results_dir.exists():
        return []

    # Sort files by modification time, newest first
    for file_path in sorted(results_dir.glob("eval-run-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            runs.append(
                RunSummary(
                    run_id=data.get("run_id", file_path.stem),
                    timestamp=data.get("timestamp", ""),
                    evaluator_name=data.get("evaluator_name", "Unknown"),
                    total_scenarios=data.get("total_scenarios", 0),
                    passed_scenarios=data.get("passed_scenarios", 0),
                    failed_scenarios=data.get("failed_scenarios", 0),
                    top_1_accuracy=data.get("top_1_accuracy", 0.0),
                    top_3_accuracy=data.get("top_3_accuracy", 0.0),
                    avg_latency_ms=data.get("avg_latency_ms", 0.0),
                )
            )
        except Exception as exc:
            logger.warning("Failed parsing run report %s: %s", file_path.name, exc)

    return runs


@router.get(
    "/runs/{run_id}",
    response_model=EvaluationRunReport,
    summary="Get full report for a specific benchmark run",
)
def get_run(run_id: str) -> EvaluationRunReport:
    """Retrieve full evaluation report by run_id."""
    results_dir = get_default_results_dir()
    # Check exact file
    run_file = results_dir / f"{run_id}.json"
    if not run_file.exists():
        # Check if run_id is 'latest' or 'baseline_latest'
        if run_id in ("latest", "baseline_latest"):
            run_file = results_dir / "baseline_latest.json"

    if not run_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark run '{run_id}' not found",
        )

    try:
        with open(run_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return EvaluationRunReport.model_validate(data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed loading run report '{run_id}': {exc}",
        )


@router.post(
    "/run",
    response_model=EvaluationRunReport,
    summary="Execute a benchmark evaluation run",
)
async def trigger_benchmark_run(req: BenchmarkTriggerRequest = BenchmarkTriggerRequest()) -> EvaluationRunReport:
    """Execute the evaluation benchmark suite against ground-truth scenarios.
    
    Guarantees:
    - Runs actual evaluation code against real scenarios in eval/scenarios/.
    - Never fabricates results or scores.
    - Idempotency / Concurrency Guard: rejects duplicate concurrent runs with HTTP 409.
    - Persists report to eval/results/ upon completion.
    """
    global _is_running_benchmark

    if _is_running_benchmark:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A benchmark run is already in progress. Please wait for it to complete.",
        )

    async with _benchmark_lock:
        _is_running_benchmark = True
        try:
            # Run in thread pool to prevent blocking asyncio loop
            loop = asyncio.get_running_loop()
            runner = EvaluationRunner(evaluator_name=req.evaluator_name)
            report = await loop.run_in_executor(
                None,
                lambda: runner.run(save_results=req.save_results),
            )
            return report
        except Exception as exc:
            logger.error("Benchmark run failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Benchmark evaluation failed: {exc}",
            )
        finally:
            _is_running_benchmark = False


@router.get(
    "/comparative",
    summary="Get comparative evaluation summary (Baseline vs LLM vs LLM+RAG)",
)
def get_comparative_eval() -> Dict[str, Any]:
    """Retrieve comparative evaluation results across modes (Baseline, LLM, LLM+RAG)."""
    results_dir = get_default_results_dir()
    comp_file = results_dir / "comparative_evaluation_week2.json"
    if not comp_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparative evaluation results not found",
        )

    try:
        with open(comp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed loading comparative results: {exc}",
        )
