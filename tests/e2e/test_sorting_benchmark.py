"""End-to-end tests for the sorting benchmark example.

These tests validate the full pipeline: config loading, C++ compilation,
execution, and metric parsing using the sorting_benchmark example.
LLM providers are mocked — no API keys required.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from llm4ad.config.schema import AppConfig, EvalContext

# Root of the repository
REPO_ROOT = Path(__file__).resolve().parents[2]
SORTING_BENCHMARK_DIR = REPO_ROOT / "examples" / "applications" / "sorting_benchmark"
SORTING_ALGORITHM_DIR = SORTING_BENCHMARK_DIR / "sorting_algorithm"
DATASET_FILE = SORTING_BENCHMARK_DIR / "data" / "small" / "1000.txt"


def _has_gpp() -> bool:
    """Check if g++ is available on the system."""
    try:
        result = subprocess.run(
            ["g++", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_gpp = pytest.mark.skipif(
    not _has_gpp(), reason="g++ compiler not available"
)


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
        """Verify the sorting benchmark config loads and validates."""
        config = AppConfig.from_yaml(str(SORTING_BENCHMARK_DIR / "config.yaml"))
        assert config.project_name == "sorting_benchmark"
        assert len(config.providers) >= 1
        assert config.coder.type in ("custom", "claude_code")
        assert config.evolution.max_generations >= 1

    def test_evaluator_config(self):
        """Verify evaluator section parses correctly."""
        config = AppConfig.from_yaml(str(SORTING_BENCHMARK_DIR / "config.yaml"))
        assert config.evaluator.type == "executable"
        assert config.evaluator.executable == "build/sorting_benchmark"
        assert config.evaluator.timeout > 0
        assert config.evaluator.dataset is not None
        assert len(config.evaluator.metric_patterns) >= 1

    def test_dataset_files_exist(self):
        """Verify the expected dataset files are present."""
        assert DATASET_FILE.exists(), f"Dataset not found: {DATASET_FILE}"
        content = DATASET_FILE.read_text(encoding="utf-8").strip()
        lines = content.splitlines()
        assert len(lines) > 0, "Dataset file is empty"
        # Each line should be an integer
        int(lines[0])


# ---------------------------------------------------------------------------
# SortingEvaluator — compile and run
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@requires_gpp
class TestSortingEvaluatorCompileRun:
    """Tests that compile and run C++ sorting code."""

    @pytest.fixture(autouse=True)
    def _setup_project(self, tmp_path):
        """Copy the sorting_algorithm template to a temp directory."""
        self.project_root = tmp_path / "sorting_algorithm"
        shutil.copytree(SORTING_ALGORITHM_DIR, self.project_root)
        yield
        # Cleanup handled by tmp_path

    def _import_evaluator(self):
        """Import and instantiate SortingEvaluator."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sorting_evaluator",
            str(SORTING_BENCHMARK_DIR / "sorting_evaluator.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.SortingEvaluator()

    @pytest.mark.asyncio
    async def test_compile_and_run_bubble_sort(self):
        """Compile the default bubble sort and verify correct output."""
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

    @pytest.mark.asyncio
    async def test_incorrect_sort_returns_zero_score(self):
        """Write a broken sort and verify score=0."""
        # Overwrite sort_impl.h with a no-op (doesn't sort)
        impl_file = self.project_root / "include" / "sort_impl.h"
        impl_file.write_text(
            '#include <vector>\n'
            '#include "sort_interface.h"\n'
            "SortResult sort(std::vector<int>& data) {\n"
            "    SortResult result = {0, 0};\n"
            "    // Intentionally do NOT sort\n"
            "    return result;\n"
            "}\n",
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

    @pytest.mark.asyncio
    async def test_compile_error_returns_zero_score(self):
        """Write invalid C++ and verify compilation failure is handled."""
        impl_file = self.project_root / "include" / "sort_impl.h"
        impl_file.write_text(
            "THIS IS NOT VALID C++ CODE !!!\n",
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
        assert "compilation failed" in result.error_message.lower()
