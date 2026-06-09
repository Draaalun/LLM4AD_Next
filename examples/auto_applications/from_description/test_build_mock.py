#!/usr/bin/env python3
"""Verify the config-based build pipeline end-to-end using a mock LLM.

This script exercises the full workflow:
  1. generate_build_config() — creates a YAML template
  2. load_build_config()     — parses the completed config
  3. Full pipeline (analyze → create → validate → write) with MockProvider
  4. Verify output directory structure and run debug_run.py

No real API key is needed — the MockProvider returns pre-crafted responses.

Usage:
    python test_build_mock.py
"""

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from llm4ad.builder.analyzer import TaskAnalyzer  # noqa: E402
from llm4ad.builder.builder_config import (  # noqa: E402
    generate_build_config,
    load_build_config,
)
from llm4ad.builder.creator import TaskCreator  # noqa: E402
from llm4ad.builder.validator import TaskValidator  # noqa: E402
from llm4ad.builder.writer import write_task_directory  # noqa: E402
from llm4ad.infra.provider.base import BaseProvider, GenerationResult  # noqa: E402

# ======================================================================
# Mock provider with canned responses
# ======================================================================

MOCK_ANALYSIS_RESPONSE = json.dumps({
    "problem_type": "sorting",
    "project_name": "sorting_task",
    "background": (
        "We aim to evolve efficient sorting algorithms for integer arrays. "
        "The goal is to minimize the number of comparisons and swaps while "
        "maintaining correctness."
    ),
    "function_name": "sort_array",
    "function_signature": "def sort_array(data: list) -> dict:",
    "function_description": (
        "Sort a list of integers in ascending order. Return a dict with "
        "'sorted': the sorted list, 'comparisons': int, 'swaps': int."
    ),
    "metrics": [
        {"name": "correctness", "type": "maximize", "weight": 1.0,
         "description": "1.0 if sorted correctly, 0.0 otherwise"},
        {"name": "comparisons", "type": "minimize", "weight": 0.3,
         "description": "Number of comparisons made"},
        {"name": "execution_time_ms", "type": "minimize", "weight": 0.1,
         "description": "Execution time in milliseconds"},
    ],
    "input_format": "A JSON object with key 'array' containing a list of integers",
    "output_format": "A JSON object with keys 'sorted', 'comparisons', 'swaps'",
    "algorithm_dir_name": "sorting_algorithm",
    "algorithm_file_name": "sort.py",
    "needs_dataset": True,
    "dataset_description": "JSON files each containing an integer array to sort",
})

MOCK_CREATION_RESPONSE = '''
===EVALUATOR_CODE===
"""Sorting evaluator for LLM4AD."""

import asyncio
import json
import sys
import time
from pathlib import Path

from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvalContext,
    EvaluationResult,
    Metric,
    MetricType,
)


@BaseEvaluator.register("sorting_task_evaluator")
class SortingTaskEvaluator(BaseEvaluator):
    """Evaluator for sorting algorithm evolution."""

    def __init__(self):
        """Initialize metrics."""
        self._metrics = [
            Metric(name="correctness", type=MetricType.MAXIMIZE, weight=1.0,
                   description="1.0 if sorted correctly, 0.0 otherwise"),
            Metric(name="comparisons", type=MetricType.MINIMIZE, weight=0.3,
                   description="Number of comparisons made"),
            Metric(name="execution_time_ms", type=MetricType.MINIMIZE, weight=0.1,
                   description="Execution time in milliseconds"),
        ]

    @property
    def name(self) -> str:
        """Get evaluator name."""
        return "sorting_task_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get metric definitions."""
        return self._metrics

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate a sorting algorithm via subprocess."""
        start_time = time.time()
        try:
            project_root = Path(cfg.project_root)
            data_path = Path(cfg.data_path)

            if not data_path.exists():
                return EvaluationResult(score=0.0, metrics={}, success=False,
                                        error_message=f"Data not found: {data_path}")

            algo_dir = project_root / "sorting_algorithm"
            if not algo_dir.exists():
                if (project_root / "sort.py").exists():
                    algo_dir = project_root
                else:
                    return EvaluationResult(score=0.0, metrics={}, success=False,
                                            error_message="Algorithm not found")

            input_json = json.dumps({"algo_dir": str(algo_dir), "data_path": str(data_path)})
            evaluator_script = str(Path(__file__).resolve())

            proc = await asyncio.create_subprocess_exec(
                sys.executable, evaluator_script, input_json,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=cfg.timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return EvaluationResult(score=0.0, metrics={}, success=False,
                                        error_message="Timeout")

            duration_ms = (time.time() - start_time) * 1000
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return EvaluationResult(score=0.0, metrics={}, success=False,
                                        error_message=f"Subprocess rc={proc.returncode}")

            result = json.loads(stdout_text.strip())
            if "error" in result:
                return EvaluationResult(score=0.0, metrics={}, success=False,
                                        error_message=result["error"])

            correctness = float(result.get("correctness", 0.0))
            comparisons = float(result.get("comparisons", 0))
            score = correctness

            return EvaluationResult(
                score=score,
                metrics={"correctness": correctness, "comparisons": comparisons,
                         "execution_time_ms": duration_ms},
                success=True, duration_ms=duration_ms)

        except Exception as e:
            return EvaluationResult(score=0.0, metrics={}, success=False,
                                    error_message=str(e),
                                    duration_ms=(time.time() - start_time) * 1000)

    @staticmethod
    def _run_algorithm(algo_dir: Path, data_path: Path) -> dict:
        """Run sorting algorithm in subprocess."""
        import importlib.util

        with open(data_path, encoding="utf-8") as f:
            test_data = json.load(f)

        arr = test_data.get("array", [])
        expected = sorted(arr)

        module_file = algo_dir / "sort.py"
        if not module_file.exists():
            return {"error": f"sort.py not found in {algo_dir}"}

        spec = importlib.util.spec_from_file_location("_algo", str(module_file))
        if spec is None or spec.loader is None:
            return {"error": "Cannot load module"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.sort_array(arr)
        is_correct = result.get("sorted") == expected
        return {"correctness": 1.0 if is_correct else 0.0,
                "comparisons": result.get("comparisons", 0),
                "swaps": result.get("swaps", 0)}


def _subprocess_main() -> None:
    """Subprocess entry point."""
    if len(sys.argv) < 2:
        sys.exit(1)
    input_data = json.loads(sys.argv[1])
    algo_dir = Path(input_data["algo_dir"])
    data_path = Path(input_data["data_path"])
    try:
        result = SortingTaskEvaluator._run_algorithm(algo_dir, data_path)
    except Exception as exc:
        result = {"error": str(exc)}
    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()

===ALGORITHM_CODE===
#!/usr/bin/env python3
"""Sorting algorithm with EVOLVE markers."""

import json
import sys

# EVOLVE_START
def sort_array(data: list) -> dict:
    """Sort a list of integers. Return sorted list with comparison/swap counts."""
    arr = list(data)
    comparisons = 0
    swaps = 0
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            comparisons += 1
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swaps += 1
    return {"sorted": arr, "comparisons": comparisons, "swaps": swaps}
# EVOLVE_END


def process(data):
    """Fixed wrapper."""
    result = sort_array(data)
    return result


def main():
    """Subprocess entry point."""
    if len(sys.argv) < 2:
        print("Usage: python sort.py '<json>'", file=sys.stderr)
        sys.exit(1)
    input_data = json.loads(sys.argv[1])
    result = process(input_data)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

===DEBUG_RUN===
#!/usr/bin/env python3
"""Quick local test for the sorting task."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sorting_algorithm"))
from sort import sort_array

test_input = [5, 3, 8, 1, 9, 2, 7, 4, 6, 0]
result = sort_array(test_input)

print(f"Input:       {test_input}")
print(f"Sorted:      {result['sorted']}")
print(f"Comparisons: {result['comparisons']}")
print(f"Swaps:       {result['swaps']}")
print(f"Correct:     {result['sorted'] == sorted(test_input)}")

===TEST_EVALUATOR===
"""Test the SortingTaskEvaluator end-to-end."""

import asyncio
from pathlib import Path

from sorting_task_evaluator import SortingTaskEvaluator

from llm4ad.config.schema import EvalContext


async def test_evaluator():
    """Run evaluator on the sample data."""
    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "sample" / "instance_001.json"
    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False
    evaluator = SortingTaskEvaluator()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(current_dir),
        timeout=120.0,
    )
    result = await evaluator.evaluate(cfg)
    print(f"Success: {result.success}")
    print(f"Score: {result.score}")
    print(f"Metrics: {result.metrics}")
    if result.error_message:
        print(f"Error: {result.error_message}")
    expected = ["correctness", "comparisons", "execution_time_ms"]
    has_all = all(m in result.metrics for m in expected)
    if result.success and has_all:
        print("[PASS] Test PASSED")
        return True
    print("[FAIL] Test FAILED")
    return False


if __name__ == "__main__":
    success = asyncio.run(test_evaluator())
    exit(0 if success else 1)

===SAMPLE_DATA===
{"array": [5, 3, 8, 1, 9, 2, 7, 4, 6, 0]}

===METADATA===
{"evaluator_class_name": "SortingTaskEvaluator", "evaluator_register_name": "sorting_task_evaluator"}
'''

MOCK_MULTIMODAL_ANALYSIS_RESPONSE = json.dumps({
    "problem_type": "sorting",
    "project_name": "sorting_task_multimodal",
    "background": (
        "We aim to evolve efficient sorting algorithms for integer arrays "
        "with visualization of sorting behavior."
    ),
    "function_name": "sort_array",
    "function_signature": "def sort_array(data: list) -> dict:",
    "function_description": (
        "Sort a list of integers in ascending order. Return a dict with "
        "'sorted': the sorted list, 'comparisons': int, 'swaps': int."
    ),
    "metrics": [
        {"name": "correctness", "type": "maximize", "weight": 1.0,
         "description": "1.0 if sorted correctly, 0.0 otherwise"},
        {"name": "comparisons", "type": "minimize", "weight": 0.3,
         "description": "Number of comparisons made"},
    ],
    "input_format": "A JSON object with key 'array' containing a list of integers",
    "output_format": "A JSON object with keys 'sorted', 'comparisons', 'swaps'",
    "algorithm_dir_name": "sorting_algorithm",
    "algorithm_file_name": "sort.py",
    "needs_dataset": True,
    "dataset_description": "JSON files each containing an integer array to sort",
    "visualization_spec": {
        "renderer_name": "sorting_renderer",
        "visualization_label": "Sorting Steps",
        "description": "Visualize the sorting process step by step",
        "raw_data_schema": {"steps": "list of array states after each swap"},
    },
})

MOCK_MULTIMODAL_CREATION_RESPONSE = '''
===EVALUATOR_CODE===
"""Multimodal sorting evaluator for LLM4AD."""

import asyncio
import base64
import io
import json
import sys
import time
from pathlib import Path

from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvalContext,
    EvaluationResult,
    Metric,
    MetricType,
)
from llm4ad.evaluator.behavior import BehaviorData, BehaviorVisualization
from llm4ad.evaluator.renderer import BaseRenderer


@BaseRenderer.register("sorting_renderer")
class SortingRenderer(BaseRenderer):
    """Renderer for sorting algorithm visualization."""

    def render(self, raw_data: dict) -> bytes:
        """Render sorting steps as a PNG image."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        steps = raw_data.get("steps", [])
        fig, ax = plt.subplots(figsize=(8, 4))
        if steps:
            ax.bar(range(len(steps[-1])), steps[-1])
        ax.set_title("Final Sorted State")
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()


@BaseEvaluator.register("sorting_task_multimodal_evaluator")
class SortingTaskMultimodalEvaluator(BaseEvaluator):
    """Multimodal evaluator for sorting algorithm evolution."""

    def __init__(self):
        """Initialize metrics."""
        self._metrics = [
            Metric(name="correctness", type=MetricType.MAXIMIZE, weight=1.0,
                   description="1.0 if sorted correctly, 0.0 otherwise"),
            Metric(name="comparisons", type=MetricType.MINIMIZE, weight=0.3,
                   description="Number of comparisons made"),
        ]

    @property
    def name(self) -> str:
        """Get evaluator name."""
        return "sorting_task_multimodal_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get metric definitions."""
        return self._metrics

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate a sorting algorithm via subprocess."""
        start_time = time.time()
        behavior_storage = getattr(cfg, "behavior_storage", "none")
        try:
            correctness = 1.0
            comparisons = 10
            duration_ms = (time.time() - start_time) * 1000

            observation_text = _build_observation_text(correctness, comparisons)
            behavior = None

            if behavior_storage == "rendered":
                img_bytes = _render_result_image({"steps": [[5, 3, 1], [1, 3, 5]]})
                viz = BehaviorVisualization(
                    label="Sorting Steps",
                    image_base64=base64.b64encode(img_bytes).decode(),
                    mime_type="image/png",
                )
                behavior = BehaviorData(
                    observation_text=observation_text,
                    visualizations=[viz],
                )
            elif behavior_storage == "raw":
                behavior = BehaviorData(
                    observation_text=observation_text,
                    raw_data={"steps": [[5, 3, 1], [1, 3, 5]]},
                    renderer_name="sorting_renderer",
                )
            else:
                behavior = BehaviorData(observation_text=observation_text)

            return EvaluationResult(
                score=correctness,
                metrics={"correctness": correctness, "comparisons": comparisons},
                success=True, duration_ms=duration_ms,
                behavior=behavior,
            )
        except Exception as e:
            return EvaluationResult(score=0.0, metrics={}, success=False,
                                    error_message=str(e))


def _render_result_image(raw_data: dict) -> bytes:
    """Render sorting visualization as PNG bytes."""
    renderer = SortingRenderer()
    return renderer.render(raw_data)


def _build_observation_text(correctness: float, comparisons: int) -> str:
    """Build compact observation text for LLM feedback."""
    return f"correctness={correctness}, comparisons={comparisons}"


if __name__ == "__main__":
    pass

===ALGORITHM_CODE===
#!/usr/bin/env python3
"""Sorting algorithm with EVOLVE markers."""

import json
import sys

# EVOLVE_START
def sort_array(data: list) -> dict:
    """Sort a list of integers. Return sorted list with comparison/swap counts."""
    arr = list(data)
    comparisons = 0
    swaps = 0
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            comparisons += 1
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swaps += 1
    return {"sorted": arr, "comparisons": comparisons, "swaps": swaps}
# EVOLVE_END


def process(data):
    """Fixed wrapper."""
    result = sort_array(data)
    return result


def main():
    """Subprocess entry point."""
    if len(sys.argv) < 2:
        print("Usage: python sort.py '<json>'", file=sys.stderr)
        sys.exit(1)
    input_data = json.loads(sys.argv[1])
    result = process(input_data)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

===DEBUG_RUN===
#!/usr/bin/env python3
"""Quick local test for the sorting task."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sorting_algorithm"))
from sort import sort_array

test_input = [5, 3, 8, 1, 9, 2, 7, 4, 6, 0]
result = sort_array(test_input)

print(f"Input:       {test_input}")
print(f"Sorted:      {result['sorted']}")
print(f"Comparisons: {result['comparisons']}")
print(f"Swaps:       {result['swaps']}")
print(f"Correct:     {result['sorted'] == sorted(test_input)}")

===TEST_EVALUATOR===
"""Test the SortingTaskMultimodalEvaluator end-to-end."""

import asyncio
from pathlib import Path

from sorting_task_multimodal_evaluator import SortingTaskMultimodalEvaluator

from llm4ad.config.schema import EvalContext


async def test_evaluator():
    """Run multimodal evaluator on sample data."""
    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "sample" / "instance_001.json"
    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False
    evaluator = SortingTaskMultimodalEvaluator()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(current_dir),
        timeout=120.0,
    )
    result = await evaluator.evaluate(cfg)
    print(f"Success: {result.success}")
    print(f"Score: {result.score}")
    print(f"Metrics: {result.metrics}")
    expected = ["correctness", "comparisons"]
    has_all = all(m in result.metrics for m in expected)
    if result.success and has_all:
        print("[PASS] Test PASSED")
        return True
    print("[FAIL] Test FAILED")
    return False


if __name__ == "__main__":
    success = asyncio.run(test_evaluator())
    exit(0 if success else 1)

===SAMPLE_DATA===
{"array": [5, 3, 8, 1, 9, 2, 7, 4, 6, 0]}

===METADATA===
{"evaluator_class_name": "SortingTaskMultimodalEvaluator", "evaluator_register_name": "sorting_task_multimodal_evaluator"}
'''


class MockProvider(BaseProvider):
    """Mock LLM provider that returns pre-crafted responses."""

    def __init__(self):
        """Initialize mock provider."""
        super().__init__(config={"api_key": "mock", "model": "mock"})
        self._call_count = 0

    async def generate(self, prompt: str, **kwargs: Any) -> GenerationResult:
        """Return mock responses based on call order."""
        self._call_count += 1
        text = (
            MOCK_ANALYSIS_RESPONSE if self._call_count == 1
            else MOCK_CREATION_RESPONSE
        )
        return GenerationResult(text=text, model="mock")

    async def generate_stream(self, prompt: str, **kwargs: Any):
        """Not used."""
        raise NotImplementedError

    async def chat(self, messages: list, **kwargs: Any) -> GenerationResult:
        """Not used."""
        raise NotImplementedError

    async def chat_stream(self, messages: list, **kwargs: Any):
        """Not used."""
        raise NotImplementedError

    async def count_tokens(self, text: str) -> int:
        """Approximate token count."""
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Return mock model info."""
        return {"name": "mock", "context_length": 128000}


class MockMultimodalProvider(BaseProvider):
    """Mock LLM provider that returns multimodal responses."""

    def __init__(self):
        """Initialize mock provider."""
        super().__init__(config={"api_key": "mock", "model": "mock"})
        self._call_count = 0

    async def generate(self, prompt: str, **kwargs: Any) -> GenerationResult:
        """Return multimodal mock responses based on call order."""
        self._call_count += 1
        text = (
            MOCK_MULTIMODAL_ANALYSIS_RESPONSE if self._call_count == 1
            else MOCK_MULTIMODAL_CREATION_RESPONSE
        )
        return GenerationResult(text=text, model="mock")

    async def generate_stream(self, prompt: str, **kwargs: Any):
        """Not used."""
        raise NotImplementedError

    async def chat(self, messages: list, **kwargs: Any) -> GenerationResult:
        """Not used."""
        raise NotImplementedError

    async def chat_stream(self, messages: list, **kwargs: Any):
        """Not used."""
        raise NotImplementedError

    async def count_tokens(self, text: str) -> int:
        """Approximate token count."""
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Return mock model info."""
        return {"name": "mock", "context_length": 128000}


# ======================================================================
# Tests
# ======================================================================

async def test_generate_build_config(tmpdir: Path):
    """Test that generate_build_config creates a valid YAML template."""
    print("[Test 1] generate_build_config()...")

    # Without description
    path = generate_build_config(tmpdir / "empty_template.yaml")
    assert path.exists(), "Template file not created"
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert "builder" in data, "Missing 'builder' section"
    assert "task" in data, "Missing 'task' section"
    print("  Template without description: OK")

    # With description
    path = generate_build_config(
        tmpdir / "prefilled.yaml",
        description="Evolve sorting algorithms\nthat minimize comparisons",
    )
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert "sorting" in data["task"]["description"].lower(), "Description not pre-filled"
    print("  Template with description: OK")
    print("  PASSED")


async def test_load_build_config(tmpdir: Path):
    """Test that load_build_config correctly parses a config file."""
    print("\n[Test 2] load_build_config()...")

    config_content = """\
builder:
  type: "openai_compatible"
  api_key: "test-key-123"
  base_url: "https://api.test.com/v1"
  model: "test-model"
  max_repair_attempts: 5

task:
  description: |
    Test problem description for sorting.
  output_dir: "./test_output"
"""
    config_path = tmpdir / "test_config.yaml"
    config_path.write_text(config_content, encoding="utf-8")

    cfg = load_build_config(config_path)
    assert cfg.builder.api_key == "test-key-123", f"Wrong api_key: {cfg.builder.api_key}"
    assert cfg.builder.model == "test-model", f"Wrong model: {cfg.builder.model}"
    assert cfg.builder.base_url == "https://api.test.com/v1"
    assert cfg.builder.max_repair_attempts == 5
    assert "sorting" in cfg.task.description.lower()
    assert cfg.task.output_dir == "./test_output"
    print("  All fields parsed correctly")
    print("  PASSED")


async def test_full_pipeline_with_config(tmpdir: Path):
    """Test the full build pipeline using config YAML + MockProvider."""
    print("\n[Test 3] Full pipeline with config YAML...")

    # Write a config YAML (simulating what a user would fill in)
    config_content = """\
builder:
  type: "openai_compatible"
  api_key: "mock-key"
  base_url: "https://mock.api.com/v1"
  model: "mock-model"
  max_repair_attempts: 1

task:
  description: |
    Evolve efficient sorting algorithms for integer arrays.
  output_dir: "{output_dir}"
""".format(output_dir=str(tmpdir / "build_output").replace("\\", "/"))

    config_path = tmpdir / "build_config.yaml"
    config_path.write_text(config_content, encoding="utf-8")

    # Load the config
    cfg = load_build_config(config_path)
    print(f"  Loaded config: model={cfg.builder.model}, output={cfg.task.output_dir}")

    # Run the pipeline with MockProvider (same as before)
    provider = MockProvider()
    description = cfg.task.description

    # Stage 1: Analyze
    print("  [1/4] Analyzing problem...")
    analyzer = TaskAnalyzer(provider)
    analysis = await analyzer.analyze(description)
    assert analysis.project_name == "sorting_task"
    assert analysis.function_name == "sort_array"
    print(f"    project_name: {analysis.project_name}")

    # Stage 2: Create
    print("  [2/4] Generating artifacts...")
    creator = TaskCreator(provider)
    blueprint = await creator.create(analysis, description)
    assert "EVOLVE_START" in blueprint.algorithm_code
    assert "BaseEvaluator" in blueprint.evaluator_code
    print(f"    evaluator: {blueprint.evaluator_file_name}")

    # Stage 3: Validate
    print("  [3/4] Validating...")
    validator = TaskValidator(provider)
    blueprint = await validator.validate(blueprint, max_attempts=1)
    assert blueprint.validation_status == "passed", (
        f"Validation failed: {blueprint.validation_errors}"
    )
    print(f"    status: {blueprint.validation_status}")

    # Stage 4: Write
    print("  [4/4] Writing to disk...")
    task_dir = write_task_directory(blueprint, cfg.task.output_dir)
    print(f"    directory: {task_dir}")

    # Verify output structure
    assert (task_dir / "config.yaml").exists(), "config.yaml missing"
    assert (task_dir / blueprint.evaluator_file_name).exists(), "evaluator missing"
    algo_path = task_dir / blueprint.algorithm_dir_name / blueprint.algorithm_file_name
    assert algo_path.exists(), "algorithm missing"
    assert (task_dir / "debug_run.py").exists(), "debug_run.py missing"

    print("\n  Generated files:")
    for p in sorted(task_dir.rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            rel = str(p.relative_to(task_dir))
            print(f"    {rel:40s} {size:>6d} bytes")

    # Verify config is valid YAML
    config_data = yaml.safe_load(
        (task_dir / "config.yaml").read_text(encoding="utf-8")
    )
    assert config_data["project_name"] == "sorting_task"
    assert config_data["evaluator"]["type"] == "custom"
    print(f"\n  Config project_name: {config_data['project_name']}")

    # Run the debug script
    print("\n  Running debug_run.py...")
    import subprocess

    result = subprocess.run(
        [sys.executable, str(task_dir / "debug_run.py")],
        capture_output=True, text=True, timeout=10,
    )
    print(f"  stdout: {result.stdout.strip()}")
    if result.returncode != 0:
        print(f"  stderr: {result.stderr.strip()}")
    assert result.returncode == 0, f"debug_run.py failed: {result.stderr}"

    print("  PASSED")


async def test_full_pipeline_multimodal(tmpdir: Path):
    """Test the full build pipeline with multimodal=True using MockMultimodalProvider."""
    print("\n[Test 4] Full pipeline with multimodal=True...")

    provider = MockMultimodalProvider()
    description = "Evolve sorting algorithms with visualization of sorting behavior."

    # Stage 1: Analyze
    print("  [1/4] Analyzing problem (multimodal)...")
    analyzer = TaskAnalyzer(provider)
    analysis = await analyzer.analyze(description, multimodal=True)
    assert analysis.project_name == "sorting_task_multimodal"
    assert analysis.visualization_spec is not None
    assert analysis.visualization_spec["renderer_name"] == "sorting_renderer"
    print(f"    visualization_spec: {analysis.visualization_spec['renderer_name']}")

    # Stage 2: Create
    print("  [2/4] Generating multimodal artifacts...")
    creator = TaskCreator(provider)
    blueprint = await creator.create(analysis, description, multimodal=True)
    assert "EVOLVE_START" in blueprint.algorithm_code
    assert "BehaviorData" in blueprint.evaluator_code
    assert "BehaviorVisualization" in blueprint.evaluator_code
    assert "BaseRenderer" in blueprint.evaluator_code
    assert "behavior_storage" in blueprint.evaluator_code
    print(f"    evaluator: {blueprint.evaluator_file_name}")
    print("    multimodal imports: OK")

    # Stage 3: Validate
    print("  [3/4] Validating (multimodal)...")
    validator = TaskValidator(provider)
    blueprint = await validator.validate(blueprint, max_attempts=1, multimodal=True)
    assert blueprint.validation_status == "passed", (
        f"Validation failed: {blueprint.validation_errors}"
    )
    print(f"    status: {blueprint.validation_status}")

    # Stage 4: Write
    print("  [4/4] Writing to disk...")
    output_dir = str(tmpdir / "multimodal_output")
    task_dir = write_task_directory(blueprint, output_dir)
    print(f"    directory: {task_dir}")

    # Verify output structure
    assert (task_dir / "config.yaml").exists(), "config.yaml missing"
    assert (task_dir / blueprint.evaluator_file_name).exists(), "evaluator missing"
    algo_path = task_dir / blueprint.algorithm_dir_name / blueprint.algorithm_file_name
    assert algo_path.exists(), "algorithm missing"

    # Verify evaluator contains multimodal patterns
    evaluator_content = (task_dir / blueprint.evaluator_file_name).read_text(encoding="utf-8")
    assert "BehaviorData" in evaluator_content, "BehaviorData not in written evaluator"
    assert "BaseRenderer" in evaluator_content, "BaseRenderer not in written evaluator"
    assert "behavior_storage" in evaluator_content, "behavior_storage not in written evaluator"

    print("\n  Generated files:")
    for p in sorted(task_dir.rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            rel = str(p.relative_to(task_dir))
            print(f"    {rel:40s} {size:>6d} bytes")

    print("  PASSED")


async def test_runtime_validation_catches_bad_class(tmpdir: Path):
    """Test that runtime validation catches evaluator class name mismatch."""
    print("\n[Test 5] Runtime validation catches bad class name...")

    from llm4ad.builder.blueprint import TaskBlueprint

    # Create a blueprint where evaluator_class_name doesn't match actual code
    evaluator_code = '''"""Bad evaluator."""
import json
import sys

class ActualClassName:
    """This class name doesn't match what blueprint expects."""
    pass

if __name__ == "__main__":
    pass
'''
    algorithm_code = '''#!/usr/bin/env python3
"""Algorithm with EVOLVE markers."""
import json
import sys

# EVOLVE_START
def sort_array(data: list) -> dict:
    """Sort integers."""
    arr = sorted(data)
    return {"sorted": arr, "comparisons": 0, "swaps": 0}
# EVOLVE_END

def main():
    """Entry point."""
    if len(sys.argv) < 2:
        sys.exit(1)
    input_data = json.loads(sys.argv[1])
    arr = input_data if isinstance(input_data, list) else input_data.get("array", [])
    result = sort_array(arr)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''
    debug_run_code = '''#!/usr/bin/env python3
"""Debug run."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "sorting_algorithm"))
from sort import sort_array
result = sort_array([3, 1, 2])
print(f"Result: {result}")
'''
    config_yaml = '''project_name: "test_bad_class"
evaluator:
  type: "custom"
  module: "test_bad_class_evaluator:WrongClassName"
evolution:
  population_size: 10
  generations: 5
'''
    blueprint = TaskBlueprint(
        project_name="test_bad_class",
        task_description="Test task",
        evaluator_code=evaluator_code,
        algorithm_code=algorithm_code,
        config_yaml=config_yaml,
        debug_run_code=debug_run_code,
        evaluator_class_name="WrongClassName",
        evaluator_file_name="test_bad_class_evaluator.py",
        algorithm_dir_name="sorting_algorithm",
        algorithm_file_name="sort.py",
        function_to_evolve="sort_array",
        metrics=[{"name": "correctness", "type": "maximize", "weight": 1.0}],
        dataset_files={"data/sample/instance_001.json": '{"array": [3, 1, 2]}'},
        test_evaluator_code="import sys\nprint('[PASS]')\nsys.exit(0)\n",
    )

    # Validate with max_attempts=1 (no repair, just detect)
    provider = MockProvider()
    validator = TaskValidator(provider)
    result = await validator.validate(blueprint, max_attempts=1)

    assert result.validation_status == "failed", (
        f"Expected validation to fail but got: {result.validation_status}"
    )
    assert any("[runtime:import]" in e for e in result.validation_errors), (
        f"Expected [runtime:import] error, got: {result.validation_errors}"
    )
    print(f"  Caught error: {result.validation_errors[-1][:80]}...")
    print("  PASSED")


async def test_runtime_validation_catches_bad_algorithm(tmpdir: Path):
    """Test that runtime validation catches algorithm that crashes."""
    print("\n[Test 6] Runtime validation catches bad algorithm...")

    from llm4ad.builder.blueprint import TaskBlueprint

    evaluator_code = '''"""Simple evaluator."""

class SimpleEvaluator:
    """Evaluator stub."""
    pass
'''
    # Algorithm that crashes on execution
    algorithm_code = '''#!/usr/bin/env python3
"""Algorithm that crashes."""
import json
import sys

# EVOLVE_START
def sort_array(data: list) -> dict:
    """This will crash."""
    raise RuntimeError("Intentional crash for testing")
# EVOLVE_END

def main():
    """Entry point."""
    if len(sys.argv) < 2:
        sys.exit(1)
    input_data = json.loads(sys.argv[1])
    arr = input_data if isinstance(input_data, list) else input_data.get("array", [])
    result = sort_array(arr)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''
    debug_run_code = '''#!/usr/bin/env python3
"""Debug run that will crash."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "sorting_algorithm"))
from sort import sort_array
result = sort_array([3, 1, 2])
print(f"Result: {result}")
'''
    config_yaml = '''project_name: "test_bad_algo"
evaluator:
  type: "custom"
  module: "test_bad_algo_evaluator:SimpleEvaluator"
evolution:
  population_size: 10
  generations: 5
'''
    blueprint = TaskBlueprint(
        project_name="test_bad_algo",
        task_description="Test task",
        evaluator_code=evaluator_code,
        algorithm_code=algorithm_code,
        config_yaml=config_yaml,
        debug_run_code=debug_run_code,
        evaluator_class_name="SimpleEvaluator",
        evaluator_file_name="test_bad_algo_evaluator.py",
        algorithm_dir_name="sorting_algorithm",
        algorithm_file_name="sort.py",
        function_to_evolve="sort_array",
        metrics=[{"name": "correctness", "type": "maximize", "weight": 1.0}],
        dataset_files={"data/sample/instance_001.json": '{"array": [3, 1, 2]}'},
        test_evaluator_code="import sys\nprint('[PASS]')\nsys.exit(0)\n",
    )

    provider = MockProvider()
    validator = TaskValidator(provider)
    result = await validator.validate(blueprint, max_attempts=1)

    assert result.validation_status == "failed", (
        f"Expected validation to fail but got: {result.validation_status}"
    )
    # Should catch either algorithm or debug_run error
    has_runtime_error = any(
        "[runtime:algorithm]" in e or "[runtime:debug_run]" in e
        for e in result.validation_errors
    )
    assert has_runtime_error, (
        f"Expected runtime error, got: {result.validation_errors}"
    )
    print(f"  Caught error: {result.validation_errors[-1][:80]}...")
    print("  PASSED")


async def run_all_tests():
    """Run all tests."""
    tmpdir = Path(tempfile.mkdtemp(prefix="llm4ad_config_test_"))
    print(f"Working directory: {tmpdir}")

    try:
        await test_generate_build_config(tmpdir)
        await test_load_build_config(tmpdir)
        await test_full_pipeline_with_config(tmpdir)
        await test_full_pipeline_multimodal(tmpdir)
        await test_runtime_validation_catches_bad_class(tmpdir)
        await test_runtime_validation_catches_bad_algorithm(tmpdir)

        print("\n" + "=" * 60)
        print("ALL CHECKS PASSED")
        print("=" * 60)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    """Run the tests."""
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
