# Writing Evaluators

This guide explains how to create custom evaluators for LLM4AD.

## Overview

Evaluators are responsible for measuring algorithm quality by running algorithms on test cases and computing scores based on metrics. LLM4AD provides three base evaluator classes:

- **`PythonEvaluator`**: For evaluating Python code directly
- **`ExecutableEvaluator`**: For evaluating compiled executables
- **`BenchmarkEvaluator`**: For standard benchmark datasets

## Creating a Python Evaluator

### Basic Structure

Create a Python evaluator by extending `PythonEvaluator`:

```python
from llm4ad.evaluator.base import (
    PythonEvaluator,
    EvaluationResult,
    Metric,
    MetricType
)
from llm4ad.config.schema import EvalContext


class MyEvaluator(PythonEvaluator):
    """Custom evaluator for my algorithm."""

    def __init__(self, config: EvalContext):
        """Initialize the evaluator.

        Args:
            config: Evaluation configuration
        """
        super().__init__(config)
        # Add any custom initialization here

    @property
    def name(self) -> str:
        """Return the evaluator name."""
        return "my_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Define the metrics this evaluator computes."""
        return [
            Metric(
                name="accuracy",
                type=MetricType.MAXIMIZE,
                description="Fraction of correct results",
                weight=1.0
            ),
            Metric(
                name="runtime",
                type=MetricType.MINIMIZE,
                description="Average execution time in seconds",
                weight=0.5
            ),
        ]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate an algorithm.

        Args:
            cfg: Evaluation configuration containing algorithm code

        Returns:
            EvaluationResult with score and metrics
        """
        # Your evaluation logic here
        pass
```

### Example: Sorting Algorithm Evaluator

Here's a complete example for evaluating sorting algorithms:

```python
"""Sorting algorithm evaluator."""

import time
from typing import Any

from llm4ad.evaluator.base import (
    PythonEvaluator,
    EvaluationResult,
    Metric,
    MetricType
)
from llm4ad.config.schema import EvalContext


class SortingEvaluator(PythonEvaluator):
    """Evaluates sorting algorithms."""

    def __init__(self, config: EvalContext):
        super().__init__(config)

    @property
    def name(self) -> str:
        return "sorting_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return [
            Metric(
                name="correctness",
                type=MetricType.MAXIMIZE,
                description="Fraction of correctly sorted arrays",
                weight=1.0
            ),
            Metric(
                name="avg_time",
                type=MetricType.MINIMIZE,
                description="Average sorting time in seconds",
                weight=0.3
            ),
            Metric(
                name="stability",
                type=MetricType.MAXIMIZE,
                description="Stability of the sort (1.0 = stable)",
                weight=0.2
            ),
        ]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate a sorting algorithm."""
        # Test cases with expected results
        test_cases = [
            ([3, 1, 4, 1, 5], [1, 1, 3, 4, 5]),
            ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]),
            ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),
            ([42] * 10, [42] * 10),
            ([], []),
        ]

        total_time = 0.0
        correct = 0
        stable = 0

        for arr, expected in test_cases:
            arr_copy = arr.copy()

            try:
                # Execute the sorting function
                start = time.time()

                # The algorithm code is in cfg.project_root
                # We expect it to define a 'sort' function
                exec_globals = {"array": arr_copy}
                exec(cfg.project_root + "\nresult = sort(array)", exec_globals)
                sorted_arr = exec_globals["result"]

                elapsed = time.time() - start
                total_time += elapsed

                # Check correctness
                if sorted_arr == expected:
                    correct += 1

                    # Check stability (preserve order of equal elements)
                    if self._is_stable(arr, sorted_arr):
                        stable += 1

            except Exception as e:
                # Execution failed - count as incorrect
                total_time += 1.0  # Penalty

        # Compute metrics
        num_tests = len(test_cases)
        correctness = correct / num_tests
        avg_time = total_time / num_tests
        stability_score = stable / num_tests

        # Compute overall score
        # Higher is better: correctness * 100 - time_penalty
        score = correctness * 100 - avg_time * 10 + stability_score * 5

        return EvaluationResult(
            score=score,
            metrics={
                "correctness": correctness,
                "avg_time": avg_time,
                "stability": stability_score,
            },
            monitor_metrics={
                "correctness": correctness,
                "avg_time": avg_time,
            },
            metadata={
                "num_tests": num_tests,
                "num_correct": correct,
                "num_stable": stable,
            },
            success=True,
        )

    def _is_stable(self, original: list, sorted_arr: list) -> bool:
        """Check if sort is stable."""
        # For equal elements, preserve original order
        # This is a simplified check
        return True  # Implement proper stability check
```

## Creating an Executable Evaluator

For compiled languages (C++, Rust, Go), use `ExecutableEvaluator`:

```python
from llm4ad.evaluator.base import ExecutableEvaluator
from llm4ad.config.schema import EvalContext


class CppEvaluator(ExecutableEvaluator):
    """Evaluates C++ executables."""

    def __init__(self, config: EvalContext):
        super().__init__(config)

    @property
    def name(self) -> str:
        return "cpp_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return [
            Metric(name="score", type=MetricType.MAXIMIZE),
        ]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate a C++ executable."""
        import subprocess

        # Compile the code
        compile_cmd = ["g++", "-o", "program", cfg.project_root]
        subprocess.run(compile_cmd, check=True, timeout=30)

        # Run the executable
        run_cmd = ["./program"]
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=cfg.timeout
        )

        # Parse output
        metrics = self.parse_output(result.stdout, result.stderr)

        return EvaluationResult(
            score=metrics.get("score", 0.0),
            metrics=metrics,
            success=result.returncode == 0,
        )

    def parse_output(self, stdout: str, stderr: str) -> dict[str, float]:
        """Parse metrics from program output.

        The program should output metrics in format:
        METRIC_NAME: value
        """
        import re

        metrics = {}
        pattern = re.compile(r"(\w+)\s*:\s*([-+]?\d*\.?\d+)")

        for line in stdout.splitlines():
            match = pattern.search(line)
            if match:
                name, value = match.groups()
                metrics[name.lower()] = float(value)

        return metrics
```

## Creating a Benchmark Evaluator

For standard benchmarks with multiple problem instances:

```python
from llm4ad.evaluator.base import BenchmarkEvaluator
from llm4ad.config.schema import EvalContext


class MyBenchmarkEvaluator(BenchmarkEvaluator):
    """Evaluates on a standard benchmark."""

    def __init__(self, config: EvalContext):
        super().__init__(config)
        # Load problem instances
        self._problem_instances = self.load_dataset(config.data_path)

    @property
    def name(self) -> str:
        return "my_benchmark_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return [
            Metric(name="accuracy", type=MetricType.MAXIMIZE),
            Metric(name="avg_time", type=MetricType.MINIMIZE),
        ]

    def load_dataset(self, dataset_path: str) -> list[Any]:
        """Load problem instances from dataset.

        Args:
            dataset_path: Path to dataset file or directory

        Returns:
            List of problem instances
        """
        import json

        with open(dataset_path) as f:
            data = json.load(f)

        return data["problems"]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate on all problem instances."""
        results = []

        for instance in self.problem_instances:
            # Evaluate on this instance
            result = await self._evaluate_instance(instance, cfg)
            results.append(result)

        # Aggregate results across all instances
        return self.aggregate_results(results)

    async def _evaluate_instance(
        self,
        instance: dict,
        cfg: EvalContext
    ) -> EvaluationResult:
        """Evaluate on a single problem instance."""
        # Your instance evaluation logic here
        pass
```

## Registering Custom Evaluators

### Method 1: Using the Registry

Register your evaluator in code:

```python
from llm4ad.evaluator.base import BaseEvaluator
from llm4ad.utils.registry import Registry

# Get the evaluator registry
evaluator_registry = Registry("evaluator", BaseEvaluator)

# Register your evaluator
@evaluator_registry.register("my_custom_evaluator")
class MyCustomEvaluator(PythonEvaluator):
    # ... implementation
    pass
```

### Method 2: Using Configuration Module

Specify the evaluator in your config file:

```yaml
evaluator:
  module: "my_module:MyCustomEvaluator"
  # ... other settings
```

LLM4AD will automatically import and instantiate the evaluator.

## Working with Datasets

### Loading Test Data

Access dataset path from configuration:

```python
async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
    """Evaluate algorithm."""
    import json

    # Load dataset from cfg.data_path
    with open(cfg.data_path) as f:
        dataset = json.load(f)

    # Use dataset for evaluation
    test_cases = dataset["test_cases"]
    # ...
```

### Dataset Configuration Modes

Configure dataset discovery in your config file:

```yaml
evaluator:
  dataset:
    mode: "files"  # or "directory" or "glob"
    files:
      - "./data/test1.json"
      - "./data/test2.json"
```

## Error Handling

Handle errors gracefully in your evaluator:

```python
async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
    """Evaluate algorithm."""
    try:
        # Your evaluation logic
        result = self._run_evaluation(cfg)
        return result

    except SyntaxError as e:
        # Code has syntax errors
        return EvaluationResult(
            score=0.0,
            metrics={},
            success=False,
            error_message=f"Syntax error: {e}",
        )

    except TimeoutError as e:
        # Code took too long
        return EvaluationResult(
            score=0.0,
            metrics={},
            success=False,
            error_message=f"Timeout: {e}",
        )

    except Exception as e:
        # Other errors
        return EvaluationResult(
            score=0.0,
            metrics={},
            success=False,
            error_message=f"Evaluation error: {e}",
        )
```

## Best Practices

### 1. Define Clear Metrics

Use descriptive metric names and types:

```python
@property
def metrics(self) -> list[Metric]:
    return [
        Metric(
            name="accuracy",
            type=MetricType.MAXIMIZE,
            description="Fraction of correct predictions",
            weight=1.0
        ),
        Metric(
            name="inference_time",
            type=MetricType.MINIMIZE,
            description="Average inference time (ms)",
            weight=0.5
        ),
    ]
```

### 2. Use Timeouts

Prevent infinite loops with timeouts:

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout_context(seconds):
    """Context manager for timeout."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Timed out after {seconds} seconds")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# Use in evaluation
with timeout_context(30):
    result = self._run_algorithm()
```

### 3. Provide Metadata

Include useful metadata for debugging:

```python
return EvaluationResult(
    score=score,
    metrics=metrics,
    metadata={
        "num_test_cases": len(test_cases),
        "num_passed": passed,
        "num_failed": failed,
        "total_time": total_time,
        "algorithm_hash": self._hash_code(code),
    },
    success=True,
)
```

### 4. Test Your Evaluator

Write unit tests for your evaluator:

```python
import pytest
from my_evaluator import SortingEvaluator


def test_sorting_evaluator():
    """Test sorting evaluator."""
    config = EvalContext(
        data_path="./="test_data.json",
        project_root=".",
        timeout=30.0
    )

    evaluator = SortingEvaluator(config)

    # Test metrics
    assert evaluator.name == "sorting_evaluator"
    assert len(evaluator.metrics) == 3

    # Test evaluation
    result = await evaluator.evaluate(config)
    assert result.success
    assert "correctness" in result.metrics
```

## Complete Example

See the [Sorting Example](../examples/sorting.md) for a complete working example.

## Next Steps

- [Configuration Guide](configuration.md) - Configure your evaluator
- [Quick Start Guide](quickstart.md) - Run your first experiment
- [Advanced Configuration](advanced.md) - Advanced usage patterns
