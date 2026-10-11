"""Sherlog Evaluation Harness Runner.

Executes benchmark scenarios against an investigator (such as the deterministic rule-based baseline),
evaluates Top-1 and Top-3 root-cause accuracy, records diagnostics, and saves reproducible JSON reports.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.app.baseline.investigator import RuleBasedInvestigator
from eval.loader import get_default_scenarios_dir, load_scenarios
from eval.models import (
    BenchmarkScenario,
    EvaluationRunReport,
    ScenarioEvaluationResult,
)


def get_default_results_dir() -> Path:
    """Return the absolute path to the eval/results directory."""
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


class EvaluationRunner:
    """Benchmark runner evaluating incident investigators against ground-truth scenarios."""

    def __init__(
        self,
        investigator: Optional[RuleBasedInvestigator] = None,
        evaluator_name: str = "Rule-Based Deterministic Baseline",
    ):
        self.investigator = investigator or RuleBasedInvestigator()
        self.evaluator_name = evaluator_name

    def run(
        self,
        scenarios: Optional[List[BenchmarkScenario]] = None,
        scenarios_dir: Optional[Path] = None,
        save_results: bool = True,
        results_dir: Optional[Path] = None,
    ) -> EvaluationRunReport:
        """Run evaluation benchmark across all scenarios and generate run report."""
        if scenarios is None:
            scenarios = load_scenarios(scenarios_dir or get_default_scenarios_dir())

        if not scenarios:
            raise ValueError("No benchmark scenarios found to evaluate.")

        scenario_results: List[ScenarioEvaluationResult] = []
        passed_count = 0
        top_1_matches = 0
        top_3_matches = 0
        total_latency_ms = 0.0

        for scenario in scenarios:
            start_time = time.perf_counter()
            report = self.investigator.investigate(scenario.incident, scenario.evidence)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            total_latency_ms += elapsed_ms

            ranked_causes = [h.root_cause for h in report.ranked_root_causes]
            top_cause = report.top_root_cause.root_cause if report.top_root_cause else None
            confidence_str = report.top_root_cause.confidence.value if report.top_root_cause else "INSUFFICIENT_EVIDENCE"
            top_score = report.top_root_cause.score if report.top_root_cause else 0.0
            supporting = report.top_root_cause.supporting_evidence if report.top_root_cause else []
            remediation = report.top_root_cause.recommended_remediation if report.top_root_cause else None

            # Evaluation logic
            if scenario.expect_insufficient_evidence:
                # Correct behavior is explicitly refusing to diagnose without evidence
                top_1 = (report.has_sufficient_evidence is False) and (top_cause is None)
                top_3 = top_1
                passed = top_1
                failure_reason = None if passed else f"Expected insufficient evidence, but predicted '{top_cause}'"
            else:
                top_1 = (top_cause == scenario.expected_root_cause)
                top_3 = (scenario.expected_root_cause in ranked_causes[:3])
                passed = top_1
                failure_reason = None if passed else f"Expected '{scenario.expected_root_cause}', got '{top_cause}'"

            if top_1:
                top_1_matches += 1
            if top_3:
                top_3_matches += 1
            if passed:
                passed_count += 1

            result_item = ScenarioEvaluationResult(
                scenario_id=scenario.scenario_id,
                name=scenario.name,
                fault_id=scenario.fault_id,
                expected_root_cause=scenario.expected_root_cause,
                predicted_root_cause=top_cause,
                ranked_hypotheses=ranked_causes,
                top_1_match=top_1,
                top_3_match=top_3,
                confidence=confidence_str,
                score=top_score,
                evidence_count=len(scenario.evidence),
                supporting_evidence=supporting,
                recommended_remediation=remediation,
                passed=passed,
                failure_reason=failure_reason,
                execution_time_ms=round(elapsed_ms, 2),
            )
            scenario_results.append(result_item)

        total_scenarios = len(scenarios)
        failed_count = total_scenarios - passed_count
        top_1_acc = round((top_1_matches / total_scenarios) * 100.0, 1) if total_scenarios > 0 else 0.0
        top_3_acc = round((top_3_matches / total_scenarios) * 100.0, 1) if total_scenarios > 0 else 0.0
        avg_latency = round(total_latency_ms / total_scenarios, 2) if total_scenarios > 0 else 0.0

        run_id = f"eval-run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        run_report = EvaluationRunReport(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            evaluator_name=self.evaluator_name,
            total_scenarios=total_scenarios,
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            top_1_accuracy=top_1_acc,
            top_3_accuracy=top_3_acc,
            avg_latency_ms=avg_latency,
            results=scenario_results,
            failed_cases=[r for r in scenario_results if not r.passed],
        )

        if save_results:
            target_results_dir = results_dir or get_default_results_dir()
            run_file = target_results_dir / f"{run_id}.json"
            latest_file = target_results_dir / "baseline_latest.json"

            with open(run_file, "w", encoding="utf-8") as f:
                f.write(run_report.model_dump_json(indent=2))

            with open(latest_file, "w", encoding="utf-8") as f:
                f.write(run_report.model_dump_json(indent=2))

        return run_report


def print_evaluation_summary(report: EvaluationRunReport) -> None:
    """Print formatted ASCII evaluation table and diagnostics to console."""
    sep = "=" * 80
    subsep = "-" * 80

    print("\n" + sep)
    print(f"  SHERLOG EVALUATION BENCHMARK REPORT: {report.evaluator_name.upper()}")
    print(f"  Run ID: {report.run_id} | Timestamp: {report.timestamp}")
    print(sep)
    print(f"  Total Scenarios Evaluated : {report.total_scenarios}")
    print(f"  Scenarios Passed          : {report.passed_scenarios} / {report.total_scenarios}")
    print(f"  Top-1 Accuracy            : {report.top_1_accuracy:.1f}%")
    print(f"  Top-3 Accuracy            : {report.top_3_accuracy:.1f}%")
    print(f"  Average Diagnosis Latency : {report.avg_latency_ms:.2f} ms")
    print(subsep)
    print(f"{'ID':<9} | {'Fault':<20} | {'Expected Cause':<30} | {'Top-1':<5} | {'Score':<5} | {'Status'}")
    print(subsep)

    for res in report.results:
        status_tag = "PASS" if res.passed else "FAIL"
        top1_tag = "YES" if res.top_1_match else "NO"
        exp_short = (res.expected_root_cause[:28] + "..") if len(res.expected_root_cause) > 30 else res.expected_root_cause
        print(f"{res.scenario_id:<9} | {res.fault_id:<20} | {exp_short:<30} | {top1_tag:<5} | {res.score:<5.0f} | {status_tag}")

    if report.failed_cases:
        print(subsep)
        print("  FAILED / MISCLASSIFIED SCENARIOS:")
        for fail in report.failed_cases:
            print(f"    - [{fail.scenario_id}] {fail.name}")
            print(f"      Reason: {fail.failure_reason}")
    else:
        print(subsep)
        print("  All benchmark scenarios passed with 100% Top-1 accuracy!")

    print(sep + "\n")


def main() -> None:
    """CLI entrypoint for running evaluation benchmarks."""
    parser = argparse.ArgumentParser(description="Run Sherlog incident diagnosis evaluation benchmark.")
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=None,
        help="Custom path to scenarios directory (default: eval/scenarios)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save evaluation output files to eval/results/",
    )
    args = parser.parse_args()

    runner = EvaluationRunner()
    report = runner.run(
        scenarios_dir=args.scenarios_dir,
        save_results=not args.no_save,
    )
    print_evaluation_summary(report)


if __name__ == "__main__":
    main()
