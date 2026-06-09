"""Custom evaluator for Python TSP solvers (multimodal version).

This evaluator extends the text-only version by generating tour
visualizations as behavior data. These images are returned as
BehaviorData so that the multimodal evolution loop can include them
in LLM prompts, allowing the LLM to visually diagnose tour quality.

Architecture (clean separation of concerns):
- ``_run_solver``: loads and runs the solver module, validates the tour,
  computes metrics. Returns metrics + raw tour data (nodes + tour).
  No rendering, no observation text — those are separate concerns.
- ``_render_tour_image``: converts raw tour data to an annotated
  base64 PNG. Called by the deferred renderer or the subprocess.
- ``_build_observation_text``: builds LLM-readable text from metrics.
  Called in the main process after the subprocess returns.
- ``evaluate()``: orchestrates subprocess, computes score, builds
  BehaviorData using the standard multimodal pattern.

SUBPROCESS ISOLATION: The evaluator script itself is the subprocess.
``evaluate()`` spawns ``tsp_evaluator.py`` with input JSON; the
subprocess loads ``solve.py`` as a module, runs it, validates the
tour, and returns metrics + raw_behavior (or pre-rendered PNG,
depending on ``behavior_storage`` mode) via JSON stdout.
"""

import asyncio
import base64
import importlib.util
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from llm4ad.config.schema import EvalContext
from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvaluationResult,
    Metric,
    MetricType,
)
from llm4ad.evaluator.behavior import BehaviorData, BehaviorVisualization
from llm4ad.evaluator.renderer import BaseRenderer

# ---------------------------------------------------------------------------
# Visualization helpers (TSP-specific)
# ---------------------------------------------------------------------------


def _render_tour_image(
    nodes: list[list[float]],
    tour: list[int],
    tour_length: float,
    n_nodes: int,
) -> str:
    """Render a TSP tour as an annotated base64 PNG image.

    Pure rendering function — converts tour data to a matplotlib plot.
    Used by both the deferred renderer and the subprocess (for
    ``"rendered"`` mode).

    Args:
        nodes: List of [x, y] coordinate pairs.
        tour: List of node indices in visitation order.
        tour_length: Total Euclidean tour length.
        n_nodes: Number of cities.

    Returns:
        Base64-encoded PNG string.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    coords = np.array(nodes)
    fig, ax = plt.subplots(figsize=(8, 8))

    # Draw tour edges
    for i in range(len(tour)):
        start = coords[tour[i]]
        end = coords[tour[(i + 1) % len(tour)]]
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color="#2563eb",
            linewidth=1.5,
            alpha=0.7,
            zorder=1,
        )

    # Draw cities
    ax.scatter(
        coords[:, 0],
        coords[:, 1],
        s=60,
        c="#3b82f6",
        edgecolors="#1e3a5f",
        linewidths=0.8,
        zorder=2,
    )

    # Highlight start city
    if tour:
        start_coord = coords[tour[0]]
        ax.scatter(
            [start_coord[0]],
            [start_coord[1]],
            s=120,
            c="#ef4444",
            edgecolors="#7f1d1d",
            linewidths=1.2,
            zorder=3,
            label=f"Start (city {tour[0]})",
        )

    # Label cities for small instances
    if n_nodes <= 30:
        for i, (x, y) in enumerate(coords):
            ax.annotate(
                str(i),
                (x, y),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=7,
                color="#374151",
                zorder=4,
            )

    # Add padding to axis limits
    x_min, x_max = coords[:, 0].min(), coords[:, 0].max()
    y_min, y_max = coords[:, 1].min(), coords[:, 1].max()
    x_pad = max((x_max - x_min) * 0.08, 2.0)
    y_pad = max((y_max - y_min) * 0.08, 2.0)
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)

    ax.set_title(
        f"TSP Tour (n={n_nodes})\nLength: {tour_length:.2f}",
        fontsize=12,
    )
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _build_observation_text(
    n_nodes: int,
    tour_length: float,
    execution_time_ms: float,
    valid: bool,
    dataset: str,
) -> str:
    """Build a human/LLM-readable observation text from TSP results.

    Args:
        n_nodes: Number of cities in the instance.
        tour_length: Total Euclidean tour length.
        execution_time_ms: Solver execution time in milliseconds.
        valid: Whether the tour is valid.
        dataset: Dataset file name for identification.

    Returns:
        Formatted observation string.
    """
    instance_name = Path(dataset).stem
    return (
        f"{instance_name} | N={n_nodes} | Length={tour_length:.2f} | "
        f"Time={execution_time_ms:.1f}ms | "
        f"Valid={'Yes' if valid else 'No'}"
    )


# ---------------------------------------------------------------------------
# Deferred renderer (for raw mode — registered in BaseRenderer registry)
# ---------------------------------------------------------------------------
# When behavior_storage is "raw", the evaluator stores compact tour data
# (nodes + tour indices, ~1 KB) instead of pre-rendered PNGs (~40 KB).
# This renderer reconstructs the image on demand using the same
# _render_tour_image() helper above. Register your renderer name to
# match the "renderer" field in BehaviorVisualization.
#
# raw_data schema:
#   {
#       "nodes": list[list[float]],   # [[x1,y1], [x2,y2], ...] city coords
#       "tour": list[int],             # [0, 3, 1, 2, ...] visitation order
#       "tour_length": float,          # Total Euclidean distance
#       "n_nodes": int                 # Number of cities
#   }


@BaseRenderer.register("tsp_tour")
class TSPTourRenderer(BaseRenderer):
    """Render a TSP tour image from stored solution data.

    Converts raw tour data (nodes + tour indices) back into an
    annotated matplotlib plot identical to the one the evaluator
    generates at evaluation time.
    """

    def render(self, raw_data: dict[str, Any], **kwargs: Any) -> str:
        """Render raw tour data to an annotated base64 PNG.

        Args:
            raw_data: Dict with ``nodes``, ``tour``, ``tour_length``,
                ``n_nodes`` keys.
            **kwargs: Unused.

        Returns:
            Base64-encoded PNG string.
        """
        nodes = raw_data["nodes"]
        tour = raw_data["tour"]
        tour_length = raw_data.get("tour_length", 0.0)
        n_nodes = raw_data.get("n_nodes", len(nodes))

        return _render_tour_image(nodes, tour, tour_length, n_nodes)


# ---------------------------------------------------------------------------
# Evaluator class
# ---------------------------------------------------------------------------


@BaseEvaluator.register("python_tsp_evaluator_multimodal")
class PythonTSPEvaluatorMultimodal(BaseEvaluator):
    """Evaluator for Python TSP solvers with tour visualization.

    Extends the base TSP evaluator to generate tour plot images.
    After the solver subprocess returns a tour, the evaluator renders
    a matplotlib visualization of cities and edges, producing a visual
    tour that the LLM can analyze for quality diagnosis.
    """

    def __init__(self):
        """Initialize the evaluator with metric definitions."""
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
        return "python_tsp_evaluator_multimodal"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    # ------------------------------------------------------------------
    # Solver loading (like LunarLander's _load_policy_module)
    # ------------------------------------------------------------------

    def _load_solver_module(self, project_root: Path):
        """Load a solver module from a given project directory.

        Args:
            project_root: Path to the directory containing solve.py.

        Returns:
            The loaded solver module with a ``solve()`` function.
        """
        solve_script = project_root / "solve.py"
        if not solve_script.exists():
            raise FileNotFoundError(f"solve.py not found in {project_root}")

        module_name = f"_solver_{id(self)}_{hash(str(solve_script))}"
        spec = importlib.util.spec_from_file_location(
            module_name, str(solve_script),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {solve_script}")

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # ------------------------------------------------------------------
    # Pure execution: run solver, validate, compute metrics
    # ------------------------------------------------------------------

    def _calculate_tour_length(self, nodes, tour):
        """Calculate the total length of a TSP tour.

        Args:
            nodes: List of (x, y) coordinate tuples.
            tour: List of node indices representing the tour.

        Returns:
            Total tour length as float.
        """
        if len(tour) < 2:
            return 0.0

        total = 0.0
        coords = np.array(nodes)

        for i in range(len(tour) - 1):
            total += np.linalg.norm(coords[tour[i]] - coords[tour[i + 1]])

        # Return to start
        total += np.linalg.norm(coords[tour[-1]] - coords[tour[0]])

        return total

    def _validate_tour(self, n_nodes, tour):
        """Validate that a tour is a valid Hamiltonian cycle.

        Args:
            n_nodes: Number of nodes in the problem.
            tour: List of node indices representing the tour.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not tour:
            return False, "Empty tour"

        if len(tour) != n_nodes:
            return False, f"Tour length {len(tour)} != number of nodes {n_nodes}"

        unique_nodes = set(tour)
        if len(unique_nodes) != n_nodes:
            return False, "Tour contains duplicate or missing nodes"

        if any(i < 0 or i >= n_nodes for i in tour):
            return False, "Tour contains invalid node indices"

        return True, None

    def _run_solver(self, solver_module, nodes: list) -> dict:
        """Run a TSP solver and return metrics + raw tour data.

        Pure execution — loads the solver, runs it on the instance,
        validates the tour, computes metrics. No rendering, no
        observation text — those are separate concerns.

        Args:
            solver_module: Loaded Python module with a ``solve()`` function.
            nodes: List of [x, y] coordinate pairs.

        Returns:
            Dict with metrics and tour data. Contains ``"error"`` key
            on failure, or full results on success::

                {
                    "tour": list[int],
                    "tour_length": float,
                    "n_nodes": int,
                    "nodes": list[list[float]],
                    "valid_tour": 1.0,
                    "execution_time_ms": float,
                }
        """
        n_nodes = len(nodes)
        run_start = time.time()

        try:
            result = solver_module.solve(nodes)
        except Exception as exc:
            return {
                "error": f"Solver raised exception: {exc}",
                "valid_tour": 0.0,
                "execution_time_ms": (time.time() - run_start) * 1000,
            }

        exec_time_ms = (time.time() - run_start) * 1000

        tour = result.get("tour", [])
        reported_length = result.get("tour_length")

        # Validate tour
        is_valid, error_msg = self._validate_tour(n_nodes, tour)
        if not is_valid:
            return {
                "error": f"Invalid tour: {error_msg}",
                "valid_tour": 0.0,
                "execution_time_ms": exec_time_ms,
            }

        # Calculate and verify tour length
        calculated_length = self._calculate_tour_length(nodes, tour)

        if reported_length is not None:
            length_diff = abs(calculated_length - reported_length)
            if length_diff > 1e-6:
                return {
                    "error": (
                        f"Reported tour length {reported_length} "
                        f"!= calculated {calculated_length}"
                    ),
                    "valid_tour": 0.0,
                    "execution_time_ms": exec_time_ms,
                }

        return {
            "tour": tour,
            "tour_length": float(calculated_length),
            "n_nodes": n_nodes,
            "nodes": nodes,
            "valid_tour": 1.0,
            "execution_time_ms": exec_time_ms,
        }

    # ------------------------------------------------------------------
    # Main process side: subprocess orchestration + BehaviorData
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate a Python TSP solver with tour visualization.

        Follows the standard multimodal evaluator pattern:
        - Steps 1-2: Validate + load instance data
        - Step 3: Locate solver script
        - Step 4: Spawn subprocess (tsp_evaluator.py itself)
        - Step 5: Score + metrics computation
        - Step 6: Build BehaviorData from subprocess result

        Args:
            cfg: EvalContext with project_root, data_path, timeout,
                and behavior_storage mode.

        Returns:
            EvaluationResult with BehaviorData containing the tour image.
        """
        start_time = time.time()

        try:
            project_root = Path(cfg.project_root)
            data_path = Path(cfg.data_path)

            # --- Step 1: Validate data file ---
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # --- Step 2: Load instance data ---
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

            # --- Step 3: Verify solver exists ---
            solve_script = project_root / "solve.py"
            if not solve_script.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"solve.py not found in {project_root}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # --- Step 4: Spawn subprocess ---
            input_json = json.dumps({
                "project_root": str(project_root),
                "nodes": nodes,
                "behavior_storage": cfg.behavior_storage,
            })

            evaluator_script = str(Path(__file__).resolve())

            proc = await asyncio.create_subprocess_exec(
                sys.executable, evaluator_script, input_json,
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

            duration_ms = (time.time() - start_time) * 1000
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=(
                        f"Subprocess failed (rc={proc.returncode}): "
                        f"{stderr_text[:500]}"
                    ),
                    duration_ms=duration_ms,
                )

            # --- Parse subprocess output ---
            try:
                result = json.loads(stdout_text.strip())
            except json.JSONDecodeError:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Invalid JSON output: {stdout_text[:200]}",
                    duration_ms=duration_ms,
                )

            if "error" in result:
                return EvaluationResult(
                    score=0.0,
                    metrics={
                        "valid_tour": result.get("valid_tour", 0.0),
                        "execution_time_ms": result.get(
                            "execution_time_ms", duration_ms,
                        ),
                    },
                    success=False,
                    error_message=result["error"],
                    duration_ms=duration_ms,
                )

            # --- Step 5: Compute score and metrics ---
            calculated_length = result["tour_length"]

            metrics = {
                "tour_length": calculated_length,
                "valid_tour": 1.0,
                "execution_time_ms": result["execution_time_ms"],
            }

            score = -calculated_length

            # --- Step 6: Build BehaviorData (multimodal addition) ---
            behavior = None
            behavior_storage = cfg.behavior_storage

            if behavior_storage != "none":
                # 6a. Build observation text from subprocess metrics
                obs_text = _build_observation_text(
                    n_nodes=n_nodes,
                    tour_length=calculated_length,
                    execution_time_ms=result["execution_time_ms"],
                    valid=True,
                    dataset=str(data_path),
                )

                # 6b. Create BehaviorVisualization based on storage mode
                viz = None
                if behavior_storage == "rendered":
                    image_b64 = result.get("image_base64")
                    if image_b64:
                        viz = BehaviorVisualization(
                            label="TSP Tour",
                            media_type="image/png",
                            data_base64=image_b64,
                        )
                elif behavior_storage == "raw":
                    tour = result.get("tour")
                    if tour is not None:
                        viz = BehaviorVisualization(
                            label="TSP Tour",
                            media_type="image/png",
                            raw_data={
                                "nodes": nodes,
                                "tour": tour,
                                "tour_length": float(calculated_length),
                                "n_nodes": n_nodes,
                            },
                            renderer="tsp_tour",
                        )

                # 6c. Package into BehaviorData
                if viz is not None:
                    behavior = BehaviorData(
                        observation=obs_text,
                        visualizations=[viz],
                        instance_id=str(data_path),
                    )

            return EvaluationResult(
                score=score,
                metrics=metrics,
                success=True,
                duration_ms=duration_ms,
                behavior=behavior,
                metadata={
                    "dataset": str(data_path),
                    "n_nodes": n_nodes,
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


# ---------------------------------------------------------------------------
# Subprocess entry point
# ---------------------------------------------------------------------------


def _subprocess_main() -> None:
    """Run the TSP solver in an isolated subprocess.

    Behavior depends on the ``behavior_storage`` mode from the input JSON:
    - ``"none"``:     Run solver, validate, return metrics only.
    - ``"raw"``:      Run solver, validate, return metrics + tour data
                      (nodes included for deferred rendering).
    - ``"rendered"``: Run solver, validate, render tour to PNG in subprocess,
                      return metrics + image_base64.
    """
    if len(sys.argv) < 2:
        print("Usage: python tsp_evaluator.py '<json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    project_root = Path(input_data["project_root"])
    nodes = input_data["nodes"]
    behavior_storage = input_data.get("behavior_storage", "rendered")

    evaluator = PythonTSPEvaluatorMultimodal()

    try:
        mod = evaluator._load_solver_module(project_root)
        if not hasattr(mod, "solve"):
            result = {"error": "solve function not found in solver module"}
        else:
            result = evaluator._run_solver(mod, nodes)

            # For "rendered" mode: render in subprocess so the main
            # process receives a compact PNG instead of raw tour data.
            if (
                behavior_storage == "rendered"
                and "error" not in result
                and "tour" in result
            ):
                result["image_base64"] = _render_tour_image(
                    result["nodes"],
                    result["tour"],
                    result["tour_length"],
                    result["n_nodes"],
                )
                # Remove nodes from result — main process already has them
                del result["nodes"]

    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()
