"""Multimodal evaluator template for Python design tasks in LLM4AD.

HOW TO USE THIS TEMPLATE:
    1. Copy this file and rename (e.g. my_task_evaluator.py)
    2. Search for "TODO" — each marks a location you MUST customize
    3. Lines without TODO are reusable boilerplate (don't change)
    4. Reference in YAML config: module: "my_evaluator.py:MyTaskEvaluatorMultimodal"

MULTIMODAL ADDITIONS (vs. text-only template):
    This template extends the base evaluator template with behavior data
    generation. After scoring an algorithm, it builds ``BehaviorData``
    containing:
    - **Observation text**: compact, LLM-readable summary of the result
    - **Visualizations**: images showing algorithm behavior (e.g., contour
      plots with search trajectories, tour maps, lander descent paths)

    Three behavior storage modes are supported (set in YAML config):
    - ``"rendered"``: Pre-render image as base64 PNG (largest, instant display)
    - ``"raw"``: Store compact data + renderer name (smallest, render on demand)
    - ``"none"``: No behavior saved (must re-run to visualize)

Architecture (clean separation of concerns):
- ``_run_algorithm``: runs the algorithm on input data, validates
  results, computes metrics. Returns metrics + raw behavior data
  (trajectory, best_point). No rendering, no observation text —
  those are separate concerns.
- ``_render_result_image``: converts raw data to an annotated
  base64 PNG. Called by the deferred renderer or the subprocess.
- ``_build_observation_text``: builds LLM-readable text from metrics.
  Called in the main process after the subprocess returns.
- ``evaluate()``: orchestrates subprocess, computes score, builds
  BehaviorData using the standard multimodal pattern.

SUBPROCESS ISOLATION:
    All evaluations run in a subprocess for fault isolation. LLM-generated
    code may segfault, deadlock, call sys.exit(), or leak memory — none of
    these can crash the main orchestrator when running in a subprocess.

    This template uses the self-spawning pattern — the evaluate() method
    spawns this file as a subprocess, and the __main__ block at the bottom
    acts as the subprocess entry point. Adapt as needed for your task.

COMMON DATA FORMAT:
    One JSON file per instance. Each evaluate() call receives one JSON file
    via cfg.data_path. The dispatcher discovers files and aggregates results.

WORKTREE COMPATIBILITY:
    In production, the algorithm file lives in a git worktree (flat layout):
    - Local:    project_root/my_algorithm/my_function.py
    - Worktree: project_root/my_function.py
    Always check both paths.
"""

import asyncio
import base64
import importlib.util
import io
import json
import math
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

# ===========================================================================
# Visualization helpers (task-specific)
# ===========================================================================
# These functions generate the behavior data that the multimodal evolution
# loop embeds in LLM prompts. The LLM can then visually diagnose algorithm
# behavior and propose targeted improvements.
#
# TODO: Replace _render_result_image() with your domain-specific rendering.
# TODO: Adapt _build_observation_text() fields to your task's key metrics.


def _render_result_image(
    grid: list[list[float]],
    x_range: list[float],
    y_range: list[float],
    grid_size: list[int],
    trajectory: list[list[float]],
    best_point: list[float],
    best_value: float,
) -> str:
    """Render the optimization result as a base64 PNG image.

    TODO: Replace this visualization with your domain-specific rendering.
    This function should produce an image that helps the LLM understand
    algorithm behavior (e.g., where it searched, where it got stuck).

    Args:
        grid: 2D grid of function values.
        x_range: [x_min, x_max] domain bounds.
        y_range: [y_min, y_max] domain bounds.
        grid_size: [n_rows, n_cols] grid dimensions.
        trajectory: List of [x, y, f_value] search points.
        best_point: [x, y] of the proposed minimum.
        best_value: Function value at the best point.

    Returns:
        Base64-encoded PNG string.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_rows, n_cols = grid_size
    xs = np.linspace(x_range[0], x_range[1], n_cols)
    ys = np.linspace(y_range[0], y_range[1], n_rows)
    xx, yy = np.meshgrid(xs, ys)
    zz = np.array(grid)

    fig, ax = plt.subplots(figsize=(8, 8))

    # Draw filled contour plot of the function landscape
    contour = ax.contourf(xx, yy, zz, levels=30, cmap="viridis", alpha=0.8)
    fig.colorbar(contour, ax=ax, label="f(x, y)")
    ax.contour(xx, yy, zz, levels=15, colors="white", linewidths=0.3, alpha=0.5)

    # Draw search trajectory as connected points
    if trajectory:
        traj = np.array(trajectory)
        ax.plot(
            traj[:, 0], traj[:, 1],
            "o-", color="#ef4444", markersize=3, linewidth=0.8,
            alpha=0.7, label=f"Trajectory ({len(trajectory)} pts)",
        )

    # Highlight the best point found
    if best_point:
        ax.scatter(
            [best_point[0]], [best_point[1]],
            s=200, marker="*", c="#fbbf24", edgecolors="#92400e",
            linewidths=1.5, zorder=5,
            label=f"Best: f={best_value:.4f}",
        )

    ax.set_xlim(x_range[0], x_range[1])
    ax.set_ylim(y_range[0], y_range[1])
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(
        f"2D Function Optimization\nBest value: {best_value:.4f} "
        f"at ({best_point[0]:.3f}, {best_point[1]:.3f})",
        fontsize=11,
    )
    ax.legend(loc="upper right", fontsize=8)
    ax.set_aspect("equal")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _build_observation_text(
    instance_name: str,
    best_value: float,
    true_minimum: float,
    n_evaluations: int,
    execution_time_ms: float,
) -> str:
    """Build LLM-readable observation text summarizing the result.

    TODO: Adapt observation fields to your task's key metrics.
    Keep it compact: 1-2 lines, pipe-separated key metrics.

    Best practices:
    - Include the instance identifier for context
    - Include the primary metric the LLM should optimize
    - Include secondary diagnostics (gap, time, validity)
    - Use consistent formatting across instances

    Args:
        instance_name: Name or path of the data instance.
        best_value: Function value at the proposed minimum.
        true_minimum: Known optimal value.
        n_evaluations: Number of function evaluations used.
        execution_time_ms: Algorithm execution time.

    Returns:
        Formatted observation string.
    """
    gap = best_value - true_minimum
    return (
        f"{instance_name} | Best={best_value:.4f} | Optimum={true_minimum:.4f} | "
        f"Gap={gap:.4f} | Evals={n_evaluations} | Time={execution_time_ms:.1f}ms"
    )


# ===========================================================================
# Deferred renderer (for raw mode)
# ===========================================================================
# When behavior_storage is "raw", the evaluator stores compact structured
# data instead of pre-rendered PNGs. This renderer converts that raw data
# back into an image on demand (e.g., when building an LLM prompt or
# displaying in the frontend).
#
# The register name here MUST match the ``renderer`` field in
# ``BehaviorVisualization`` created by the evaluator below.
#
# raw_data schema (this template — 2D function optimization):
#   {
#       "grid": list[list[float]],        # 2D grid of function values
#       "x_range": [float, float],         # x-axis domain bounds
#       "y_range": [float, float],         # y-axis domain bounds
#       "grid_size": [int, int],           # [n_rows, n_cols]
#       "trajectory": list[list[float]],   # [[x, y, f_val], ...] search path
#       "best_point": [float, float],      # proposed minimum location
#       "best_value": float                # f(x, y) at best_point
#   }


# TODO: Rename the register name to match your task (e.g. "tsp_tour", "lander_trajectory")
@BaseRenderer.register("my_task_contour")
# TODO: Rename the class to match your task
class MyTaskContourRenderer(BaseRenderer):
    """Deferred renderer for 2D function optimization results.

    Converts compact raw data (grid + trajectory + best point) back into
    an annotated contour plot. The render() method is called on demand
    when behavior_storage is ``"raw"`` and a visualization is needed.
    """

    def render(self, raw_data: dict[str, Any], **kwargs: Any) -> str:
        """Render raw optimization data to an annotated base64 PNG.

        Args:
            raw_data: Dict matching the raw_data schema documented above.
            **kwargs: Unused (reserved for future rendering options).

        Returns:
            Base64-encoded PNG string.
        """
        # TODO: Adapt the raw_data field extraction to your task's schema
        return _render_result_image(
            grid=raw_data["grid"],
            x_range=raw_data["x_range"],
            y_range=raw_data["y_range"],
            grid_size=raw_data["grid_size"],
            trajectory=raw_data.get("trajectory", []),
            best_point=raw_data.get("best_point", [0.0, 0.0]),
            best_value=raw_data.get("best_value", 0.0),
        )


# ===========================================================================
# Evaluator class
# ===========================================================================


# TODO: Change register name to your evaluator name (must match YAML module field)
@BaseEvaluator.register("my_task_evaluator_multimodal")
# TODO: Rename class
class MyTaskEvaluatorMultimodal(BaseEvaluator):
    """Multimodal evaluator template for a custom Python design task.

    Extends the base evaluator with behavior data generation. After
    running the algorithm in a subprocess and computing metrics, it
    builds ``BehaviorData`` (observation text + visualization images)
    based on the configured ``behavior_storage`` mode.
    """

    def __init__(self):
        """Initialize evaluator with metric definitions."""
        # TODO: Define metrics for your task. Each Metric must match
        # the `metrics` list in your YAML config.
        # MetricType.MAXIMIZE = higher is better (reward, accuracy)
        # MetricType.MINIMIZE = lower is better (time, error, cost)
        self._metrics = [
            Metric(
                name="best_value",
                type=MetricType.MINIMIZE,
                weight=1.0,
                description="Function value at proposed minimum (lower is better)",
            ),
            Metric(
                name="optimality_gap",
                type=MetricType.MINIMIZE,
                weight=0.5,
                description="Distance from known optimal value",
            ),
            Metric(
                name="execution_time_ms",
                type=MetricType.MINIMIZE,
                weight=0.1,
                description="Execution time in milliseconds",
            ),
        ]

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        # TODO: Return your evaluator name (should match register name)
        return "my_task_evaluator_multimodal"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    # ------------------------------------------------------------------
    # Algorithm loading (like LunarLander's _load_policy_module)
    # ------------------------------------------------------------------

    def _load_algorithm_module(self, algo_dir: Path):
        """Load an algorithm module from a given directory.

        Args:
            algo_dir: Path to the directory containing my_function.py.

        Returns:
            The loaded algorithm module with a ``my_algorithm()`` function.
        """
        # TODO: Change "my_function.py" to your algorithm filename
        module_file = algo_dir / "my_function.py"
        if not module_file.exists():
            raise FileNotFoundError(f"my_function.py not found in {algo_dir}")

        module_name = f"_algo_{id(self)}_{hash(str(module_file))}"
        spec = importlib.util.spec_from_file_location(
            module_name, str(module_file),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {module_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # ------------------------------------------------------------------
    # Pure execution: run algorithm, validate, compute metrics
    # ------------------------------------------------------------------

    def _run_algorithm(
        self,
        algo_func,
        algo_input: dict,
        true_optimum: list[float],
        true_minimum: float,
    ) -> dict:
        """Run the algorithm on input data and return metrics + raw output.

        This method runs inside the subprocess. It ONLY handles execution
        and validation — no image rendering, no observation text. Those
        are separate concerns handled downstream.

        Args:
            algo_func: The algorithm function to call (e.g. ``my_algorithm``).
            algo_input: Dict with input fields for the algorithm (grid,
                x_range, y_range, grid_size).
            true_optimum: [x, y] of the known optimal point.
            true_minimum: Known optimal function value.

        Returns:
            Dict with result fields. Contains ``"error"`` key on failure.
        """
        start_time = time.time()

        # TODO: Adapt algorithm invocation to your function signature
        try:
            algo_result = algo_func(algo_input)
        except Exception as e:
            return {"error": f"Algorithm execution failed: {e}"}

        execution_time_ms = (time.time() - start_time) * 1000

        # --- Extract and validate results ---
        # TODO: Adapt validation to your task's output format
        trajectory = algo_result.get("trajectory", [])
        best_point = algo_result.get("best_point", [0.0, 0.0])
        best_value = algo_result.get("best_value", float("inf"))

        if best_point is None or not isinstance(best_point, (list, tuple)) or len(best_point) != 2:
            return {"error": f"Invalid best_point: {best_point}"}

        if math.isinf(best_value) or math.isnan(best_value):
            return {"error": f"Invalid best_value: {best_value}"}

        optimality_gap = best_value - true_minimum
        dist_to_optimum = math.sqrt(
            (best_point[0] - true_optimum[0]) ** 2
            + (best_point[1] - true_optimum[1]) ** 2
        )

        return {
            "best_value": best_value,
            "best_point": list(best_point),
            "optimality_gap": optimality_gap,
            "dist_to_optimum": dist_to_optimum,
            "n_evaluations": len(trajectory),
            "execution_time_ms": execution_time_ms,
            "true_minimum": true_minimum,
            # Raw behavior data (trajectory) — used for visualization
            "trajectory": trajectory,
        }

    # ------------------------------------------------------------------
    # Main process side: subprocess orchestration + BehaviorData
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate an algorithm implementation via subprocess.

        Follows the standard multimodal evaluator pattern:
        - Steps 1-2: Validate + find algorithm directory
        - Step 3: Spawn subprocess (this file itself)
        - Step 4: Parse subprocess result
        - Step 5: Compute score and metrics
        - Step 6: Build BehaviorData from subprocess result

        Args:
            cfg: EvalContext with:
                - cfg.project_root: path to algorithm directory
                - cfg.data_path: path to the data file for this instance
                - cfg.timeout: max execution time in seconds
                - cfg.behavior_storage: "rendered", "raw", or "none"

        Returns:
            EvaluationResult with score, metrics, and behavior data.
        """
        start_time = time.time()

        try:
            project_root = Path(cfg.project_root)
            data_path = Path(cfg.data_path)

            # --- Step 1: Validate data file (boilerplate) ---
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # --- Step 2: Find algorithm directory (worktree-compatible) ---
            # TODO: Change "my_algorithm" to your algorithm directory name
            # TODO: Change "my_function.py" to targeted algorithm filename
            algo_dir = project_root / "my_algorithm"
            if not algo_dir.exists():
                if (project_root / "my_function.py").exists():
                    algo_dir = project_root
                else:
                    return EvaluationResult(
                        score=0.0,
                        metrics={},
                        success=False,
                        error_message=f"Algorithm not found in {project_root}",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

            # --- Step 3: Spawn subprocess (boilerplate) ---
            input_json = json.dumps({
                "algo_dir": str(algo_dir),
                "data_path": str(data_path),
                "behavior_storage": cfg.behavior_storage,
                # TODO(optional): Add extra parameters the subprocess needs
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

            # --- Step 4: Parse subprocess output (boilerplate) ---
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
                    metrics={},
                    success=False,
                    error_message=result["error"],
                    duration_ms=duration_ms,
                )

            # --- Step 5: Compute score from subprocess result ---
            # TODO: Extract values from result dict and compute your score.
            #
            # Score convention (higher is always better for evolution):
            #   MINIMIZE tasks: score = -value
            #   MAXIMIZE tasks: score = value
            best_value = result.get("best_value", float("inf"))
            true_minimum = result.get("true_minimum", 0.0)
            optimality_gap = best_value - true_minimum
            exec_time = result.get("execution_time_ms", duration_ms)

            # Negate because lower best_value is better
            score = -best_value

            # TODO: Build metrics dict matching your _metrics definitions
            metrics_dict = {
                "best_value": best_value,
                "optimality_gap": optimality_gap,
                "execution_time_ms": exec_time,
            }

            # --- Step 6: Build BehaviorData (multimodal addition) ---
            behavior = None
            behavior_storage = cfg.behavior_storage
            instance_name = Path(data_path).stem

            if behavior_storage != "none":
                # 6a. Build observation text from subprocess metrics
                obs_text = _build_observation_text(
                    instance_name=instance_name,
                    best_value=best_value,
                    true_minimum=true_minimum,
                    n_evaluations=result.get("n_evaluations", 0),
                    execution_time_ms=exec_time,
                )

                # 6b. Create BehaviorVisualization based on storage mode
                viz = None
                if behavior_storage == "rendered":
                    # Subprocess already rendered the image
                    image_b64 = result.get("image_base64")
                    if image_b64:
                        viz = BehaviorVisualization(
                            # TODO: Change visualization label
                            label="Function Optimization",
                            media_type="image/png",
                            data_base64=image_b64,
                        )
                elif behavior_storage == "raw":
                    # Store compact raw data for deferred rendering
                    # TODO: Adapt raw_data fields to your task
                    viz = BehaviorVisualization(
                        # TODO: Change visualization label
                        label="Function Optimization",
                        media_type="image/png",
                        raw_data={
                            "grid": result.get("grid", []),
                            "x_range": result.get("x_range", [-5.0, 5.0]),
                            "y_range": result.get("y_range", [-5.0, 5.0]),
                            "grid_size": result.get("grid_size", [50, 50]),
                            "trajectory": result.get("trajectory", []),
                            "best_point": result.get("best_point", [0.0, 0.0]),
                            "best_value": best_value,
                        },
                        # TODO: Must match register name above
                        renderer="my_task_contour",
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
                metrics=metrics_dict,
                success=True,
                duration_ms=duration_ms,
                behavior=behavior,
                metadata={
                    "dataset": str(data_path),
                    "instance": instance_name,
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
    """Run a single evaluation in an isolated subprocess.

    Behavior depends on the ``behavior_storage`` mode from the input JSON:
    - ``"none"``:     Run algorithm, return metrics only.
    - ``"raw"``:      Run algorithm, return metrics + grid/trajectory data
                      for deferred rendering.
    - ``"rendered"``: Run algorithm, render image in subprocess, return
                      metrics + image_base64 (avoids transferring large
                      grid data over the pipe).
    """
    if len(sys.argv) < 2:
        print("Usage: python my_evaluator.py '<json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    algo_dir = Path(input_data["algo_dir"])
    data_path = Path(input_data["data_path"])
    behavior_storage = input_data.get("behavior_storage", "rendered")

    # --- Load data ---
    # TODO: Adapt to your data format
    with open(data_path, encoding="utf-8") as f:
        test_data = json.load(f)

    grid = test_data.get("grid", [])
    x_range = test_data.get("x_range", [-5.0, 5.0])
    y_range = test_data.get("y_range", [-5.0, 5.0])
    grid_size = test_data.get("grid_size", [50, 50])
    true_optimum = test_data.get("true_optimum", [0.0, 0.0])
    true_minimum = test_data.get("true_minimum", 0.0)

    evaluator = MyTaskEvaluatorMultimodal()

    try:
        # TODO: Change "my_algorithm" to your function name
        mod = evaluator._load_algorithm_module(algo_dir)
        if not hasattr(mod, "my_algorithm"):
            result = {"error": "my_algorithm function not found in module"}
        else:
            algo_input = {
                "grid": grid,
                "x_range": x_range,
                "y_range": y_range,
                "grid_size": grid_size,
            }
            result = evaluator._run_algorithm(
                mod.my_algorithm, algo_input, true_optimum, true_minimum,
            )

            # Handle behavior_storage modes
            if "error" not in result:
                if behavior_storage == "rendered":
                    # Render in subprocess to avoid transferring large
                    # grid data over the pipe
                    result["image_base64"] = _render_result_image(
                        grid=grid,
                        x_range=x_range,
                        y_range=y_range,
                        grid_size=grid_size,
                        trajectory=result.get("trajectory", []),
                        best_point=result.get("best_point", [0.0, 0.0]),
                        best_value=result.get("best_value", 0.0),
                    )
                    # Don't send trajectory/grid — main process doesn't
                    # need them in rendered mode
                    result.pop("trajectory", None)
                elif behavior_storage == "raw":
                    # Include grid data for deferred rendering
                    result["grid"] = grid
                    result["x_range"] = x_range
                    result["y_range"] = y_range
                    result["grid_size"] = grid_size
                elif behavior_storage == "none":
                    # Strip visualization data — not needed
                    result.pop("trajectory", None)

    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()
