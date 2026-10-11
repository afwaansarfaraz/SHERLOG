"""Scenario loader and validator for the Sherlog evaluation framework."""

import json
from pathlib import Path
from typing import List
from eval.models import BenchmarkScenario


def get_default_scenarios_dir() -> Path:
    """Return the absolute path to the eval/scenarios directory."""
    return Path(__file__).resolve().parent / "scenarios"


def load_scenarios(scenarios_dir: Path = None) -> List[BenchmarkScenario]:
    """Load and validate all JSON benchmark scenario files from directory.

    Args:
        scenarios_dir: Directory containing scenario JSON files. Defaults to eval/scenarios/.

    Returns:
        List of validated BenchmarkScenario objects sorted by scenario_id.
    """
    target_dir = scenarios_dir or get_default_scenarios_dir()
    if not target_dir.exists():
        return []

    scenarios: List[BenchmarkScenario] = []
    for file_path in sorted(target_dir.glob("*.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            scenario = BenchmarkScenario.model_validate(data)
            scenarios.append(scenario)
        except Exception as err:
            raise ValueError(f"Failed to load scenario file '{file_path.name}': {err}") from err

    return scenarios
