"""Unit and integration tests for the Sherlog evaluation runner harness."""

import pytest
from pathlib import Path
from eval import EvaluationRunner, load_scenarios
from eval.models import BenchmarkScenario


def test_load_benchmark_scenarios():
    """All benchmark scenarios in eval/scenarios must load and validate cleanly."""
    scenarios = load_scenarios()
    assert len(scenarios) >= 10, f"Expected at least 10 scenarios, loaded {len(scenarios)}"

    scenario_ids = [s.scenario_id for s in scenarios]
    assert len(scenario_ids) == len(set(scenario_ids)), "Scenario IDs must be unique"

    fault_ids = {s.fault_id for s in scenarios}
    expected_faults = {
        "db_pool_exhaustion",
        "slow_query",
        "dependency_timeout",
        "traffic_spike",
        "configuration_error",
        "memory_leak",
    }
    assert expected_faults.issubset(fault_ids), f"Missing expected fault scenarios: {expected_faults - fault_ids}"


def test_run_baseline_evaluation_harness():
    """Execute deterministic baseline against all benchmark scenarios and verify accuracy."""
    runner = EvaluationRunner()
    report = runner.run(save_results=False)

    assert report.total_scenarios >= 10
    assert report.failed_scenarios == 0, f"Failed scenarios: {[f.scenario_id for f in report.failed_cases]}"
    assert report.top_1_accuracy == 100.0
    assert report.top_3_accuracy == 100.0
    assert report.avg_latency_ms < 50.0  # Deterministic rules run in under 50ms per case


def test_evaluation_runner_reports_failures_accurately(tmp_path):
    """When a scenario is misclassified or does not match expected, runner reports failure reason."""
    # Create an artificially mismatched scenario
    mismatched = BenchmarkScenario(
        scenario_id="SCN-TEST-FAIL",
        fault_id="slow_query",
        name="Artificially Mismatched Ground Truth Test",
        description="Testing failure reporting mechanism in runner",
        service="orders",
        expected_root_cause="some_nonexistent_root_cause",  # Deliberately mismatched
        incident={
            "title": "Slow query alert",
            "service": "orders",
            "summary": "Queries taking long",
            "metadata": {"alertname": "SlowQueryDetected"},
        },
        evidence=[],
    )

    runner = EvaluationRunner()
    report = runner.run(scenarios=[mismatched], save_results=False)

    assert report.total_scenarios == 1
    assert report.failed_scenarios == 1
    assert report.top_1_accuracy == 0.0
    assert len(report.failed_cases) == 1
    assert "Expected 'some_nonexistent_root_cause'" in report.failed_cases[0].failure_reason


def test_evaluation_runner_saves_results(tmp_path):
    """Evaluation runner must persist reproducible JSON artifacts."""
    runner = EvaluationRunner()
    report = runner.run(save_results=True, results_dir=tmp_path)

    saved_files = list(tmp_path.glob("*.json"))
    assert len(saved_files) >= 2  # run_id.json and baseline_latest.json
