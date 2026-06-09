"""End-to-end tests for the Python sorting benchmark example.

These tests validate the full pipeline: config loading, Python execution,
and metric parsing using the Python sorting_benchmark example.
LLM providers are mocked — no API keys required.
"""

import os
import shutil
from pathlib import Path

import pytest

from llm4ad.config.schema import AppConfig, EvalContext

# Root of the repository
REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_SORTING_BENCHMARK_DIR = REPO_ROOT / "examples" / "applications" / "sorting_benchmark_python"
PYTHON_SORTING_ALGORITHM_DIR = PYTHON_SORTING_BENCHMARK_DIR / "sorting_algorithm"
DATASET_FILE = PYTHON_SORTING_BENCHMARK_DIR / "data" / "small" / "test_001.txt"


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
    """Tests for loading config.yaml."""

    def test_load_yaml(self):
        """Verify the Python sorting benchmark config loads and validates."""
        config = AppConfig.from_yaml(str(PYTHON_SORTING_BENCHMARK_DIR / "config.yaml"))
        assert config.project_name == "sorting_benchmark_python"
        assert len(config.providers) >= 1
        assert config.coder.type in ("custom", "claude_code")
        assert config.evolution.max_generations >= 1

    def test_evaluator_config(self):
        """Verify evaluator section parses correctly."""
        config = AppConfig.from_yaml(str(PYTHON_SORTING_BENCHMARK_DIR / "config.yaml"))
        assert config.evaluator.module is not None
        assert config.evaluator.timeout > 0
        assert config.evaluator.dataset is not None

    def test_dataset_files_exist(self):
        """Verify the expected dataset files are present."""
        assert DATASET_FILE.exists(), f"Dataset not found: {DATASET_FILE}"
        content = DATASET_FILE.read_text(encoding="utf-8").strip()
        # Verify it's a valid text file with integers
        lines = content.splitlines()
        assert len(lines) > 0, "Dataset file is empty"
        # Each line should be an integer
        int(lines[0])


# ---------------------------------------------------------------------------
# PythonSortingEvaluator — execute and validate
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestPythonSortingEvaluator:
    """Tests that execute and validate Python sorting code."""

    @pytest.fixture(autouse=True)
    def _setup_project(self, tmp_path):
        """Copy the sorting_algorithm template to a temp directory."""
        self.project_root = tmp_path / "sorting_algorithm"
        shutil.copytree(PYTHON_SORTING_ALGORITHM_DIR, self.project_root)
        yield
        # Cleanup handled by tmp_path

    def _import_evaluator(self):
        """Import and instantiate PythonSortingEvaluator."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sorting_evaluator",
            str(PYTHON_SORTING_BENCHMARK_DIR / "sorting_evaluator.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.PythonSortingEvaluator()

    @pytest.mark.asyncio
    async def test_run_bubble_sort(self):
        """Run the default bubble sort and verify correct output."""
        evaluator = self._import_evaluator()

        cfg = EvalContext(
            data_path=str(DATASET_FILE),
            project_root=str(self.project_root),
            timeout=60.0,
        )
        result = await evaluator.evaluate(cfg)

        assert result.success, f"Evaluation failed: {result.error_message}"
        assert result.score != 0.0  # Non-zero score (negative for MINIMIZE metrics)
        assert result.metrics.get("correct") == 1.0
        assert result.metrics.get("comparisons", 0) > 0
        assert result.metrics.get("swaps", 0) >= 0
        # Verify execution time was recorded
        assert result.metrics.get("execution_time_ms", 0) > 0

    @pytest.mark.asyncio
    async def test_incorrect_sort_returns_zero_score(self):
        """Write a broken sort and verify score=0."""
        # Overwrite sort.py with a no-op (doesn't sort)
        sort_file = self.project_root / "sort.py"
        sort_file.write_text(
            '''#!/usr/bin/env python3
import sys
import json

def sort(data):
    # Intentionally do NOT sort
    return {
        "result": data,  # Return unsorted data
        "comparisons": 0,
        "swaps": 0,
    }

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    input_data = json.loads(sys.argv[1])
    result = sort(input_data)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
''',
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
        assert "incorrect" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_syntax_error_returns_zero_score(self):
        """Write invalid Python and verify syntax error is handled."""
        # Overwrite sort.py with invalid Python syntax
        sort_file = self.project_root / "sort.py"
        sort_file.write_text(
            '''#!/usr/bin/env python3
THIS IS NOT VALID PYTHON SYNTAX !!!
''',
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
            "test_001.txt",
            "test_002.txt",
            "test_003.txt",
        ]

        for dataset_file in dataset_files:
            data_path = PYTHON_SORTING_BENCHMARK_DIR / "data" / "small" / dataset_file
            if not data_path.exists():
                continue

            cfg = EvalContext(
                data_path=str(data_path),
                project_root=str(self.project_root),
                timeout=60.0,
            )
            result = await evaluator.evaluate(cfg)

            assert result.success, f"Evaluation failed for {dataset_file}: {result.error_message}"
            assert result.metrics.get("correct") == 1.0, f"Sorting incorrect for {dataset_file}"

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
        expected_metrics = ["execution_time_ms", "comparisons", "swaps", "correct"]
        for metric in expected_metrics:
            assert metric in result.metrics, f"Missing metric: {metric}"

        # Verify metric values are reasonable
        assert result.metrics["comparisons"] > 0, "Should have at least some comparisons"
        assert result.metrics["swaps"] >= 0, "Swaps should be non-negative"
        assert result.metrics["correct"] == 1.0, "Should be marked as correct"
        assert result.metrics["execution_time_ms"] > 0, "Should have recorded execution time"
