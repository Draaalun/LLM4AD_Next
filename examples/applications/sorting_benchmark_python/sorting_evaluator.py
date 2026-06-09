"""Custom evaluator for Python sorting algorithms.

This evaluator inherits from BaseEvaluator and handles execution
and result parsing for Python sorting algorithm implementations.

Uses asyncio.create_subprocess_exec() instead of subprocess.run()
so that multiple instance evaluations can run truly in parallel
when dispatched via asyncio.gather().
"""

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


@BaseEvaluator.register("python_sorting_evaluator")
class PythonSortingEvaluator(BaseEvaluator):
    """Evaluator for Python sorting algorithms.

    Executes the provided sorting implementation against a dataset
    and parses performance metrics.
    """

    def __init__(self):
        """Initialize the sorting evaluator with configuration."""
        self._metrics = [
            Metric(
                name="execution_time_ms",
                type=MetricType.MINIMIZE,
                weight=1.0,
                description="Total execution time in milliseconds",
            ),
            Metric(
                name="comparisons",
                type=MetricType.MINIMIZE,
                weight=0.5,
                description="Number of comparisons performed",
            ),
            Metric(
                name="swaps",
                type=MetricType.MINIMIZE,
                weight=0.5,
                description="Number of swaps performed",
            ),
        ]

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return "python_sorting_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate a Python sorting algorithm implementation.

        Args:
            cfg: EvalContext containing project_root and data_path.

        Returns:
            Evaluation result with performance metrics.
        """
        start_time = time.time()

        try:
            project_root = Path(cfg.project_root)
            data_path = Path(cfg.data_path)

            # Check if data file exists
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Load test data (plain text format: one integer per line)
            with open(data_path, encoding="utf-8") as f:
                test_input = [int(line.strip()) for line in f if line.strip()]

            # Compute expected output (sorted)
            expected_output = sorted(test_input)

            # Prepare input for the sorting script
            input_json = json.dumps(test_input)

            # Run the sorting algorithm
            sort_script = project_root / "sort.py"
            if not sort_script.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"sort.py not found in {project_root}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            run_start = time.time()
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(sort_script), input_json,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=cfg.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Evaluation timed out after {cfg.timeout}s",
                    duration_ms=cfg.timeout * 1000,
                )
            duration_ms = (time.time() - run_start) * 1000

            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Execution failed: {stderr_text}",
                    duration_ms=duration_ms,
                )

            # Parse output
            try:
                output_data = json.loads(stdout_text.strip())
                sorted_result = output_data.get("result", [])
                metrics = {
                    "comparisons": output_data.get("comparisons", 0),
                    "swaps": output_data.get("swaps", 0),
                }
            except json.JSONDecodeError:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Invalid JSON output: {stdout_text[:200]}",
                    duration_ms=duration_ms,
                )

            # Check correctness
            is_correct = sorted_result == expected_output
            metrics["correct"] = 1.0 if is_correct else 0.0
            metrics["execution_time_ms"] = duration_ms

            if not is_correct:
                return EvaluationResult(
                    score=0.0,
                    metrics=metrics,
                    success=False,
                    error_message=(
                        f"Sorting result is incorrect. "
                        f"Expected {expected_output[:5]}..., got {sorted_result[:5]}..."
                    ),
                    duration_ms=duration_ms,
                )

            # Compute score (lower time is better, normalized)
            # Use negative execution time as score (for maximization)
            score = -duration_ms

            return EvaluationResult(
                score=score,
                metrics=metrics,
                success=True,
                duration_ms=duration_ms,
                metadata={
                    "dataset": str(data_path),
                    "input_size": len(test_input),
                },
            )

        except Exception as e:
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=f"Evaluation error: {e}",
                duration_ms=(time.time() - start_time) * 1000,
            )
