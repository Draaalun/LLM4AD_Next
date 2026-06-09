"""Custom evaluator for Python TSP solvers.

This evaluator inherits from BaseEvaluator and handles execution
and result parsing for Python TSP solver implementations.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvalContext,
    EvaluationResult,
    Metric,
    MetricType,
)


@BaseEvaluator.register("python_tsp_evaluator")
class PythonTSPEvaluator(BaseEvaluator):
    """Evaluator for Python TSP solvers.

    Executes the provided TSP implementation against a dataset
    and parses performance metrics.
    """

    def __init__(self):
        """Initialize the TSP evaluator with configuration."""
        self._metrics = [
            Metric(
                name="tour_length",
                type=MetricType.MINIMIZE,
                weight=1.0,
                description="Total length of the TSP tour",
            ),
            Metric(
                name="execution_time_ms",
                type=MetricType.MINIMIZE,
                weight=0.3,
                description="Total execution time in milliseconds",
            ),
            Metric(
                name="valid_tour",
                type=MetricType.MAXIMIZE,
                weight=10.0,
                description="Whether the tour is valid (1.0) or invalid (0.0)",
            ),
        ]

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return "python_tsp_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    def _calculate_tour_length(self, nodes, tour):
        """Calculate the total length of a TSP tour.

        Args:
            nodes: List of (x, y) coordinate tuples
            tour: List of node indices representing the tour

        Returns:
            float: Total tour length
        """
        if len(tour) < 2:
            return 0.0

        total = 0.0
        nodes = np.array(nodes)

        for i in range(len(tour) - 1):
            total += np.linalg.norm(nodes[tour[i]] - nodes[tour[i + 1]])

        # Return to start
        total += np.linalg.norm(nodes[tour[-1]] - nodes[tour[0]])

        return total

    def _validate_tour(self, n_nodes, tour):
        """Validate that a tour is a valid Hamiltonian cycle.

        Args:
            n_nodes: Number of nodes in the problem
            tour: List of node indices representing the tour

        Returns:
            tuple: (is_valid, error_message)
        """
        if not tour:
            return False, "Empty tour"

        if len(tour) != n_nodes:
            return False, f"Tour length {len(tour)} != number of nodes {n_nodes}"

        # Check all nodes are visited exactly once
        unique_nodes = set(tour)
        if len(unique_nodes) != n_nodes:
            return False, "Tour contains duplicate or missing nodes"

        # Check all indices are valid
        if any(i < 0 or i >= n_nodes for i in tour):
            return False, "Tour contains invalid node indices"

        return True, None

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate a Python TSP solver implementation.

        Args:
            cfg: EvalContext containing project_root and data_path

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

            # Load test data
            with open(data_path, encoding="utf-8") as f:
                test_data = json.load(f)

            nodes = test_data.get("nodes", [])
            n_nodes = len(nodes)

            if n_nodes == 0:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message="No nodes in test data",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Prepare input for the TSP solver
            input_json = json.dumps({"nodes": nodes})

            # Run the TSP solver
            solve_script = project_root / "solve.py"
            if not solve_script.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"solve.py not found in {project_root}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            run_start = time.time()
            result = subprocess.run(
                [sys.executable, str(solve_script), input_json],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=cfg.timeout,
            )
            duration_ms = (time.time() - run_start) * 1000

            if result.returncode != 0:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Execution failed: {result.stderr}",
                    duration_ms=duration_ms,
                )

            # Parse output
            try:
                output_data = json.loads(result.stdout.strip())
                tour = output_data.get("tour", [])
                reported_length = output_data.get("tour_length", None)
            except json.JSONDecodeError:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Invalid JSON output: {result.stdout[:200]}",
                    duration_ms=duration_ms,
                )

            # Validate tour
            is_valid, error_msg = self._validate_tour(n_nodes, tour)
            if not is_valid:
                return EvaluationResult(
                    score=0.0,
                    metrics={
                        "valid_tour": 0.0,
                        "execution_time_ms": duration_ms,
                    },
                    success=False,
                    error_message=f"Invalid tour: {error_msg}",
                    duration_ms=duration_ms,
                )

            # Calculate tour length for verification
            calculated_length = self._calculate_tour_length(nodes, tour)

            # Verify reported length matches calculated
            if reported_length is not None:
                length_diff = abs(calculated_length - reported_length)
                if length_diff > 1e-6:
                    return EvaluationResult(
                        score=0.0,
                        metrics={
                            "valid_tour": 0.0,
                            "execution_time_ms": duration_ms,
                        },
                        success=False,
                        error_message=f"Reported tour length {reported_length} != calculated {calculated_length}",
                        duration_ms=duration_ms,
                    )

            metrics = {
                "tour_length": calculated_length,
                "valid_tour": 1.0,
                "execution_time_ms": duration_ms,
            }

            # Compute score (lower tour length is better, use negative as score)
            score = -calculated_length

            return EvaluationResult(
                score=score,
                metrics=metrics,
                success=True,
                duration_ms=duration_ms,
                metadata={
                    "dataset": str(data_path),
                    "n_nodes": n_nodes,
                },
            )

        except subprocess.TimeoutExpired:
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=f"Evaluation timed out after {cfg.timeout}s",
                duration_ms=cfg.timeout * 1000,
            )
        except Exception as e:
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=f"Evaluation error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )
