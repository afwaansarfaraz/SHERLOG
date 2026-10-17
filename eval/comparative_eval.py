"""Sherlog Comparative Evaluation Harness: Baseline vs. LLM vs. LLM+RAG.

Executes a small, standardized, reproducible evaluation set across 3 modes:
  Mode A: Rules-only deterministic baseline
  Mode B: LLM investigation without RAG
  Mode C: LLM investigation with RAG

Measures and reports:
  - Top-1 and Top-3 Root-Cause Accuracy
  - Retrieval Relevance (mean cosine similarity score)
  - Time-to-Diagnosis Latency (ms)
  - Token Usage per Case
  - Deterministic Fallback Rate (%)
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.baseline.investigator import RuleBasedInvestigator
from backend.app.db.base import Base
from backend.app.investigation.ingestion import KnowledgeIngestionManager
from backend.app.investigation.orchestrator import InvestigationPipeline
from backend.app.investigation.rag import KnowledgeRetriever
from eval.loader import load_scenarios
from eval.models import BenchmarkScenario

logger = logging.getLogger(__name__)


@dataclass
class ModeEvaluationSummary:
    mode_name: str
    total_cases: int
    top_1_matches: int
    top_1_accuracy: float
    top_3_matches: int
    top_3_accuracy: float
    avg_latency_ms: float
    avg_tokens_used: float
    fallback_count: int
    fallback_rate: float
    avg_retrieval_relevance: float
    case_results: List[Dict[str, Any]]


def run_comparative_evaluation(
    scenarios_dir: Optional[Path] = None,
    runbooks_dir: Optional[Path] = None,
    save_results: bool = True,
    output_path: Optional[Path] = None,
) -> Dict[str, ModeEvaluationSummary]:
    """Execute evaluation benchmark across Modes A, B, and C."""
    # 1. Load benchmark scenarios
    scenarios = load_scenarios(scenarios_dir)
    # Filter to known diagnostic scenarios (e.g. 5 representative core fault scenarios)
    target_faults = ["db_pool_exhaustion", "slow_query", "dependency_timeout", "traffic_spike", "insufficient_evidence"]
    eval_cases = [s for s in scenarios if any(f in s.scenario_id.lower() or f in s.fault_id.lower() for f in target_faults)]
    if not eval_cases:
        eval_cases = scenarios[:5]

    print(f"\nLoaded {len(eval_cases)} representative benchmark cases for comparative evaluation.")

    # 2. Setup isolated in-memory database with populated knowledge base
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    init_db = TestingSession()
    try:
        # Ingest runbooks into knowledge base
        r_dir = runbooks_dir or (Path(__file__).resolve().parent.parent / "docs" / "runbooks")
        if r_dir.exists():
            mgr = KnowledgeIngestionManager(db=init_db)
            mgr.ingest_directory(r_dir)
            print(f"Populated knowledge base from {r_dir}")
    finally:
        init_db.close()

    modes = ["baseline", "llm_no_rag", "llm_rag"]
    summaries: Dict[str, ModeEvaluationSummary] = {}

    for mode in modes:
        mode_label = {
            "baseline": "Mode A: Rules-Only Baseline",
            "llm_no_rag": "Mode B: LLM Investigation (No RAG)",
            "llm_rag": "Mode C: LLM Investigation (With RAG)",
        }[mode]

        print(f"\n--- Running {mode_label} ---")
        case_results: List[Dict[str, Any]] = []
        top_1_count = 0
        top_3_count = 0
        total_latency = 0.0
        total_tokens = 0
        fallback_count = 0
        relevance_scores: List[float] = []

        for scn in eval_cases:
            db = TestingSession()
            try:
                start_time = time.perf_counter()
                tokens_used = 0
                used_fallback = False
                top_relevance = 0.0
                ranked_causes: List[str] = []
                top_cause: Optional[str] = None

                if mode == "baseline":
                    # Rules-only baseline investigator
                    investigator = RuleBasedInvestigator()
                    report = investigator.investigate(scn.incident, scn.evidence)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    ranked_causes = [h.root_cause for h in report.ranked_root_causes]
                    top_cause = report.top_root_cause.root_cause if report.top_root_cause else None
                    tokens_used = 0
                    used_fallback = True  # Baseline mode is pure deterministic rules

                elif mode == "llm_no_rag":
                    # LLM without RAG
                    retriever = KnowledgeRetriever(db=db, vector_enabled=False)
                    pipeline = InvestigationPipeline(db=db, retriever=retriever)
                    inc_payload = dict(scn.incident)
                    inc_payload["id"] = f"norag-{scn.scenario_id}"
                    inc_payload["evidence"] = scn.evidence
                    result = pipeline.run(inc_payload)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    ranked_causes = [h.root_cause for h in result.ranked_hypotheses]
                    top_cause = result.root_cause
                    tokens_used = result.budget_consumed.tokens_used
                    used_fallback = (result.source == "baseline_fallback")

                elif mode == "llm_rag":
                    # LLM with real Vector RAG
                    retriever = KnowledgeRetriever(db=db, vector_enabled=True)
                    # Check retrieval relevance for query
                    rag_res = retriever.retrieve_similar_incidents(
                        service_name=scn.service,
                        incident_title=scn.incident.get("title", ""),
                        max_results=3,
                    )
                    if rag_res.documents:
                        top_relevance = rag_res.documents[0].similarity_score
                        relevance_scores.append(top_relevance)

                    pipeline = InvestigationPipeline(db=db, retriever=retriever)
                    inc_payload = dict(scn.incident)
                    inc_payload["id"] = f"rag-{scn.scenario_id}"
                    inc_payload["evidence"] = scn.evidence
                    result = pipeline.run(inc_payload)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    ranked_causes = [h.root_cause for h in result.ranked_hypotheses]
                    top_cause = result.root_cause
                    tokens_used = result.budget_consumed.tokens_used
                    used_fallback = (result.source == "baseline_fallback")

                total_latency += elapsed_ms
                total_tokens += tokens_used
                if used_fallback:
                    fallback_count += 1

                # Evaluate accuracy against expected root cause
                if scn.expect_insufficient_evidence:
                    is_top_1 = (top_cause is None or top_cause == "INSUFFICIENT_EVIDENCE")
                    is_top_3 = is_top_1
                else:
                    is_top_1 = (top_cause == scn.expected_root_cause)
                    is_top_3 = (scn.expected_root_cause in ranked_causes[:3]) or is_top_1

                if is_top_1:
                    top_1_count += 1
                if is_top_3:
                    top_3_count += 1

                case_results.append({
                    "scenario_id": scn.scenario_id,
                    "expected": scn.expected_root_cause,
                    "predicted": top_cause,
                    "top_1_match": is_top_1,
                    "top_3_match": is_top_3,
                    "latency_ms": round(elapsed_ms, 2),
                    "tokens_used": tokens_used,
                    "fallback": used_fallback,
                    "relevance_score": round(top_relevance, 4),
                })
                print(f"  [{scn.scenario_id}] Expected: {scn.expected_root_cause} | Got: {top_cause} (Top-1: {is_top_1}, {elapsed_ms:.1f}ms, {tokens_used} tok)")

            finally:
                db.close()

        total = len(eval_cases)
        summary = ModeEvaluationSummary(
            mode_name=mode_label,
            total_cases=total,
            top_1_matches=top_1_count,
            top_1_accuracy=round((top_1_count / total) * 100.0, 1),
            top_3_matches=top_3_count,
            top_3_accuracy=round((top_3_count / total) * 100.0, 1),
            avg_latency_ms=round(total_latency / total, 1),
            avg_tokens_used=round(total_tokens / total, 1),
            fallback_count=fallback_count,
            fallback_rate=round((fallback_count / total) * 100.0, 1),
            avg_retrieval_relevance=round(sum(relevance_scores) / len(relevance_scores), 4) if relevance_scores else 0.0,
            case_results=case_results,
        )
        summaries[mode] = summary

    # Print Comparative Matrix
    print("\n" + "=" * 90)
    print("SHERLOG WEEK 2 — COMPARATIVE EVALUATION MATRIX")
    print("=" * 90)
    print(f"{'Evaluation Metric':<30} | {'Mode A (Baseline)':<18} | {'Mode B (LLM No RAG)':<18} | {'Mode C (LLM + RAG)':<18}")
    print("-" * 90)
    print(f"{'Top-1 Root Cause Accuracy':<30} | {summaries['baseline'].top_1_accuracy:>16.1f}% | {summaries['llm_no_rag'].top_1_accuracy:>16.1f}% | {summaries['llm_rag'].top_1_accuracy:>16.1f}%")
    print(f"{'Top-3 Root Cause Accuracy':<30} | {summaries['baseline'].top_3_accuracy:>16.1f}% | {summaries['llm_no_rag'].top_3_accuracy:>16.1f}% | {summaries['llm_rag'].top_3_accuracy:>16.1f}%")
    print(f"{'Average Latency (ms)':<30} | {summaries['baseline'].avg_latency_ms:>16.1f}  | {summaries['llm_no_rag'].avg_latency_ms:>16.1f}  | {summaries['llm_rag'].avg_latency_ms:>16.1f} ")
    print(f"{'Average Tokens Consumed':<30} | {summaries['baseline'].avg_tokens_used:>16.1f}  | {summaries['llm_no_rag'].avg_tokens_used:>16.1f}  | {summaries['llm_rag'].avg_tokens_used:>16.1f} ")
    print(f"{'Fallback Rate':<30} | {summaries['baseline'].fallback_rate:>16.1f}% | {summaries['llm_no_rag'].fallback_rate:>16.1f}% | {summaries['llm_rag'].fallback_rate:>16.1f}%")
    print(f"{'Mean Retrieval Relevance':<30} | {'N/A':>18} | {'N/A':>18} | {summaries['llm_rag'].avg_retrieval_relevance:>18.4f}")
    print("=" * 90)

    if save_results:
        out_file = output_path or (Path(__file__).resolve().parent / "results" / "comparative_evaluation_week2.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        serializable = {k: asdict(v) for k, v in summaries.items()}
        out_file.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        print(f"\nSaved evaluation artifact to: {out_file}")

    return summaries


if __name__ == "__main__":
    run_comparative_evaluation()
