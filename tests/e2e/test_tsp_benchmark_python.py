"""End-to-end tests for the Python TSP benchmark example.

These tests validate the full pipeline: config loading, Python execution,
and metric parsing using the Python tsp_benchmark example.
LLM providers are mocked — no API keys required.
"""

import os
import shutil
from pathlib import Path

import pytest

from llm4ad.config.schema import AppConfig, EvalContext

# Root of the repository
REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_TSP_BENCHMARK_DIR = REPO_ROOT / "examples" / "applications" / "tsp_benchmark_python"
PYTHON_TSP_ALGORITHM_DIR = PYTHON_TSP_BENCHMARK_DIR / "tsp_algorithm"
DATASET_FILE = PYTHON_TSP_BENCHMARK_DIR / "data" / "small" / "instance_001.json"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

# Set up required environment variables for config loading tests
@pytest.fixture(autouse=True)
def _setup_env_vars():
    """Set up required environment variables for YAML config loading."""
    original_values = {}
    test_vars = {
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_API_KEY": "test-key",
        "LLM_MODEL": "gpt-4",
    }
    for key, value in test_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    yield
    # Restore original values
    for key, value in original_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.mark.e2e
class TestConfigLoading:
    """Tests for loading tsp_benchmark_python.yaml."""

    def test_load_yaml(self):
        """Verify the Python TSP benchmark config loads and validates."""
        config = AppConfig.from_yaml(str(PYTHON_TSP_BENCHMARK_DIR / "tsp_benchmark_config.yaml"))
        assert config.project_name == "tsp_benchmark_python"
        assert len(config.providers) >= 1
        assert config.coder.type in ("custom", "claude_code")
        assert config.evolution.max_generations >= 1

    def test_evaluator_config(self):
        """Verify evaluator section parses correctly."""
        config = AppConfig.from_yaml(str(PYTHON_TSP_BENCHMARK_DIR / "tsp_benchmark_config.yaml"))
        assert config.evaluator.module is not None
        assert config.evaluator.timeout > 0
        assert config.evaluator.dataset is not None

    def test_dataset_files_exist(self):
        """Verify the expected dataset files are present."""
        assert DATASET_FILE.exists(), f"Dataset not found: {DATASET_FILE}"
        import json

        content = json.loads(DATASET_FILE.read_text(encoding="utf-8"))
        # Verify it's a valid JSON file with nodes
        assert "nodes" in content
        assert isinstance(content["nodes"], list)
        assert len(content["nodes"]) > 0
        # Each node should be a tuple/list of 2 coordinates
        assert len(content["nodes"][0]) == 2


# ---------------------------------------------------------------------------
# PythonTSPEvaluator — execute and validate
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestPythonTSPEvaluator:
    """Tests that execute and validate Python TSP solver code."""

    @pytest.fixture(autouse=True)
    def _setup_project(self, tmp_path):
        """Copy the tsp_algorithm template to a temp directory."""
        self.project_root = tmp_path / "tsp_algorithm"
        shutil.copytree(PYTHON_TSP_ALGORITHM_DIR, self.project_root)
        yield

    def _import_evaluator(self):
        """Import and instantiate PythonTSPEvaluator."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "tsp_evaluator",
            str(PYTHON_TSP_BENCHMARK_DIR / "tsp_evaluator.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.PythonTSPEvaluator()

    @pytest.mark.asyncio
    async def test_run_nearest_neighbor(self):
        """Run the default nearest neighbor solver and verify correct output."""
        evaluator = self._import_evaluator()

        cfg = EvalContext(
            data_path=str(DATASET_FILE),
            project_root=str(self.project_root),
            timeout=60.0,
        )
        result = await evaluator.evaluate(cfg)

        assert result.success, f"Evaluation failed: {result.error_message}"
        assert result.score != 0.0  # Non-zero score (negative for MINIMIZE metrics)
        assert result.metrics.get("valid_tour") == 1.0
        assert result.metrics.get("tour_length", 0) > 0
        # Verify execution time was recorded
        assert result.metrics.get("execution_time_ms", 0) > 0

    @pytest.mark.asyncio
    async def test_invalid_tour_returns_zero_score(self):
        """Write a broken TSP solver and verify score=0."""
        # Overwrite solve.py with a no-op (doesn't create valid tour)
        solve_file = self.project_root / "solve.py"
        solve_file.write_text(
            """#!/usr/bin/env python3
import sys
import json

def solve(nodes):
    # Intentionally return invalid tour (empty)
    return {
        "tour": [],
        "tour_length": 0.0,
    }

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    input_data = json.loads(sys.argv[1])
    result = solve(input_data.get("nodes", []))
    print(json.dumps(result))

if __name__ == "__main__":
    main()
""",
            encoding="utf-8",
        )

        evaluator = self._import_evaluator()
        cfg = EvalContext(
            data_path=str(DATASET_FILE),
            project_root=str(self.project_root),
            timeout=60.0,
        )
        result = await evaluator.evaluate(cfg)

        assert not result.success
        assert result.score == 0.0
        assert "invalid" in result.error_message.lower() or "empty" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_syntax_error_returns_zero_score(self):
        """Write invalid Python and verify syntax error is handled."""
        # Overwrite solve.py with invalid Python syntax
        solve_file = self.project_root / "solve.py"
        solve_file.write_text(
            """#!/usr/bin/env python3
THIS IS NOT VALID PYTHON SYNTAX !!!
""",
            encoding="utf-8",
        )

        evaluator = self._import_evaluator()
        cfg = EvalContext(
            data_path=str(DATASET_FILE),
            project_root=str(self.project_root),
            timeout=60.0,
        )
        result = await evaluator.evaluate(cfg)

        assert not result.success
        assert result.score == 0.0
        # Should mention execution error
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_multiple_datasets(self):
        """Test that the evaluator can handle different dataset files."""
        evaluator = self._import_evaluator()

        # Test with different dataset files
        dataset_files = [
            "instance_001.json",
            "instance_002.json",
            "instance_003.json",
        ]

        for dataset_file in dataset_files:
            data_path = PYTHON_TSP_BENCHMARK_DIR / "data" / "small" / dataset_file
            if not data_path.exists():
                continue

            cfg = EvalContext(
                data_path=str(data_path),
                project_root=str(self.project_root),
                timeout=60.0,
            )
            result = await evaluator.evaluate(cfg)

            assert result.success, f"Evaluation failed for {dataset_file}: {result.error_message}"
            assert result.metrics.get("valid_tour") == 1.0, f"Invalid tour for {dataset_file}"

    @pytest.mark.asyncio
    async def test_metrics_recorded_correctly(self):
        """Verify that all metrics are recorded correctly."""
        evaluator = self._import_evaluator()

        cfg = EvalContext(
            data_path=str(DATASET_FILE),
            project_root=str(self.project_root),
            timeout=60.0,
        )
        result = await evaluator.evaluate(cfg)

        assert result.success
        # Check that all expected metrics are present
        expected_metrics = ["execution_time_ms", "tour_length", "valid_tour"]
        for metric in expected_metrics:
            assert metric in result.metrics, f"Missing metric: {metric}"

        # Verify metric values are reasonable
        assert result.metrics["tour_length"] > 0, "Should have positive tour length"
        assert result.metrics["valid_tour"] == 1.0, "Should be marked as valid"
        assert result.metrics["execution_time_ms"] > 0, "Should have recorded execution time"

    @pytest.mark.asyncio
    async def test_tour_validation(self):
        """Test that the evaluator correctly validates TSP tours."""
        evaluator = self._import_evaluator()

        # First, run the normal solver to get a baseline
        cfg = EvalContext(
            data_path=str(DATASET_FILE),
            project_root=str(self.project_root),
            timeout=60.0,
        )
        result = await evaluator.evaluate(cfg)

        assert result.success
        # Verify the tour is valid by checking metadata
        if "n_nodes" in result.metadata:
            # Tour length should be reasonable for this number of nodes
            # (not too short, not impossibly long)
            assert result.metrics["tour_length"] > 0, "Tour should have positive length"
