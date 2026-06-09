"""Multimodal evaluator for TSP tour construction heuristic evolution.

Evaluates hybrid_kdtree_two_phase_tsp by running it in a subprocess,
computing tour length, and generating tour visualizations for the LLM.
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
# Visualization helpers
# ===========================================================================


def _render_result_image(
    nodes: list[list[float]],
    tour: list[int],
    tour_length: float,
    edge_lengths: list[float],
) -> str:
    """Render the TSP tour as a base64 PNG image.

    Draws city coordinates as scatter points with the tour path as directed
    line segments. The starting city is highlighted, and edges are
    color-coded by length to reveal long detours.

    Args:
        nodes: List of [x, y] coordinate pairs.
        tour: List of node indices in visitation order.
        tour_length: Total tour length including return edge.
        edge_lengths: Euclidean length of each consecutive edge
            (including return edge). Same length as tour.

    Returns:
        Base64-encoded PNG string.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from matplotlib.colors import Normalize

    nodes_arr = np.array(nodes, dtype=np.float64)
    n = len(nodes_arr)

    fig, ax = plt.subplots(figsize=(8, 8))

    # Build full tour cycle (append return to start)
    tour_cycle = list(tour) + [tour[0]]

    # Color-code edges by length
    if edge_lengths and len(edge_lengths) > 0:
        el = np.array(edge_lengths, dtype=np.float64)
        norm = Normalize(vmin=el.min(), vmax=el.max())
        cmap = cm.get_cmap("RdYlGn_r")  # red = long, green = short

        for i in range(len(tour_cycle) - 1):
            src = tour_cycle[i]
            dst = tour_cycle[i + 1]
            edge_idx = i if i < len(edge_lengths) else len(edge_lengths) - 1
            color = cmap(norm(edge_lengths[edge_idx]))
            ax.plot(
                [nodes_arr[src, 0], nodes_arr[dst, 0]],
                [nodes_arr[src, 1], nodes_arr[dst, 1]],
                "-",
                color=color,
                linewidth=1.2,
                alpha=0.8,
            )

        # Add colorbar
        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
        cbar.set_label("Edge length", fontsize=9)
    else:
        # Fallback: uniform color
        for i in range(len(tour_cycle) - 1):
            src = tour_cycle[i]
            dst = tour_cycle[i + 1]
            ax.plot(
                [nodes_arr[src, 0], nodes_arr[dst, 0]],
                [nodes_arr[src, 1], nodes_arr[dst, 1]],
                "-",
                color="#3b82f6",
                linewidth=1.0,
                alpha=0.7,
            )

    # Draw all cities
    ax.scatter(
        nodes_arr[:, 0],
        nodes_arr[:, 1],
        s=30,
        c="#1e3a5f",
        zorder=5,
        edgecolors="white",
        linewidths=0.5,
        label=f"{n} cities",
    )

    # Label cities if few enough
    if n <= 30:
        for i in range(n):
            ax.annotate(
                str(i),
                (nodes_arr[i, 0], nodes_arr[i, 1]),
                fontsize=6,
                ha="center",
                va="bottom",
                textcoords="offset points",
                xytext=(0, 4),
            )

    # Highlight start city
    start = tour[0]
    ax.scatter(
        [nodes_arr[start, 0]],
        [nodes_arr[start, 1]],
        s=150,
        marker="*",
        c="#fbbf24",
        edgecolors="#92400e",
        linewidths=1.5,
        zorder=6,
        label=f"Start (city {start})",
    )

    # Axis setup
    pad_x = (nodes_arr[:, 0].max() - nodes_arr[:, 0].min()) * 0.05 + 1
    pad_y = (nodes_arr[:, 1].max() - nodes_arr[:, 1].min()) * 0.05 + 1
    ax.set_xlim(nodes_arr[:, 0].min() - pad_x, nodes_arr[:, 0].max() + pad_x)
    ax.set_ylim(nodes_arr[:, 1].min() - pad_y, nodes_arr[:, 1].max() + pad_y)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(
        f"TSP Tour ({n} cities)\nTotal length: {tour_length:.2f}",
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
    tour_length: float,
    n_cities: int,
    execution_time_ms: float,
    longest_edge: float,
    mean_edge: float,
) -> str:
    """Build LLM-readable observation text summarizing the TSP result.

    Args:
        instance_name: Name of the data instance.
        tour_length: Total tour length including return edge.
        n_cities: Number of cities.
        execution_time_ms: Algorithm execution time.
        longest_edge: Length of the longest edge in the tour.
        mean_edge: Mean edge length.

    Returns:
        Formatted observation string.
    """
    return (
        f"{instance_name} | Cities={n_cities} | TourLength={tour_length:.2f} | "
        f"MeanEdge={mean_edge:.2f} | LongestEdge={longest_edge:.2f} | "
        f"Time={execution_time_ms:.1f}ms"
    )


# ===========================================================================
# Deferred renderer (for raw mode)
# ===========================================================================


@BaseRenderer.register("tsp_tour")
class TSPTourRenderer(BaseRenderer):
    """Deferred renderer for TSP tour visualization.

    Converts compact raw data (nodes + tour + edge_lengths) into an
    annotated tour map PNG on demand.
    """

    def render(self, raw_data: dict[str, Any], **kwargs: Any) -> str:
        """Render raw TSP data to an annotated base64 PNG.

        Args:
            raw_data: Dict with nodes, tour, tour_length, edge_lengths.
            **kwargs: Unused.

        Returns:
            Base64-encoded PNG string.
        """
        return _render_result_image(
            nodes=raw_data["nodes"],
            tour=raw_data["tour"],
            tour_length=raw_data.get("tour_length", 0.0),
            edge_lengths=raw_data.get("edge_lengths", []),
        )


# ===========================================================================
# Evaluator class
# ===========================================================================


@BaseEvaluator.register("tsp_multimodal_evaluator")
class TSPMultimodalEvaluator(BaseEvaluator):
    """Multimodal evaluator for TSP tour construction heuristic.

    Runs hybrid_kdtree_two_phase_tsp in a subprocess, computes tour length,
    and generates tour visualizations for the LLM evolution loop.
    """

    def __init__(self):
        """Initialize evaluator with metric definitions."""
        self._metrics = [
            Metric(
                name="tour_length",
                type=MetricType.MINIMIZE,
                weight=1.0,
                description=(
                    "Total Euclidean distance of the tour including the "
                    "return edge from the last city back to the first city."
                ),
            ),
        ]

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return "tsp_multimodal_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    def _load_algorithm_module(self, algo_dir: Path):
        """Load the algorithm module from a given directory.

        Args:
            algo_dir: Path to the directory containing solve.py.

        Returns:
            The loaded module with a hybrid_kdtree_two_phase_tsp function.
        """
        module_file = algo_dir / "solve.py"
        if not module_file.exists():
            raise FileNotFoundError(f"solve.py not found in {algo_dir}")

        module_name = f"_algo_{id(self)}_{hash(str(module_file))}"
        spec = importlib.util.spec_from_file_location(
            module_name, str(module_file),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {module_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run_algorithm(
        self,
        algo_func,
        nodes: list[list[float]],
    ) -> dict:
        """Run the TSP algorithm and compute metrics.

        Args:
            algo_func: The hybrid_kdtree_two_phase_tsp function.
            nodes: List of [x, y] coordinate pairs.

        Returns:
            Dict with tour, tour_length, edge_lengths, execution_time_ms,
            or an "error" key on failure.
        """
        n = len(nodes)
        nodes_arr = np.array(nodes, dtype=np.float64)

        start_time = time.time()
        try:
            result = algo_func(nodes)
        except Exception as e:
            return {"error": f"Algorithm execution failed: {e}"}
        execution_time_ms = (time.time() - start_time) * 1000

        # The algorithm returns a list of node indices (the tour)
        if isinstance(result, dict):
            tour = result.get("result", result.get("tour", []))
        elif isinstance(result, (list, tuple)):
            tour = list(result)
        else:
            return {"error": f"Unexpected return type: {type(result)}"}

        # Validate tour
        if not isinstance(tour, list) or len(tour) == 0:
            return {"error": f"Invalid tour: empty or wrong type"}

        if len(tour) != n:
            return {
                "error": (
                    f"Tour length mismatch: got {len(tour)} "
                    f"cities, expected {n}"
                ),
            }

        tour_set = set(tour)
        if len(tour_set) != n or min(tour_set) != 0 or max(tour_set) != n - 1:
            return {"error": "Tour does not visit each city exactly once"}

        # Compute tour length and edge lengths
        edge_lengths = []
        tour_length = 0.0
        for i in range(n):
            src = tour[i]
            dst = tour[(i + 1) % n]
            dx = nodes_arr[src, 0] - nodes_arr[dst, 0]
            dy = nodes_arr[src, 1] - nodes_arr[dst, 1]
            dist = math.sqrt(dx * dx + dy * dy)
            edge_lengths.append(dist)
            tour_length += dist

        return {
            "tour": tour,
            "tour_length": tour_length,
            "edge_lengths": edge_lengths,
            "execution_time_ms": execution_time_ms,
            "n_cities": n,
        }

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate an algorithm implementation via subprocess.

        Args:
            cfg: EvalContext with project_root, data_path, timeout,
                behavior_storage.

        Returns:
            EvaluationResult with score, metrics, and behavior data.
        """
        start_time = time.time()

        try:
            project_root = Path(cfg.project_root)
            data_path = Path(cfg.data_path)

            # Step 1: Validate data file
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Step 2: Find algorithm directory (worktree-compatible)
            algo_dir = project_root / "algorithm"
            if not algo_dir.exists():
                if (project_root / "solve.py").exists():
                    algo_dir = project_root
                else:
                    return EvaluationResult(
                        score=0.0,
                        metrics={},
                        success=False,
                        error_message=(
                            f"Algorithm not found in {project_root}"
                        ),
                        duration_ms=(time.time() - start_time) * 1000,
                    )

            # Step 3: Spawn subprocess
            input_json = json.dumps({
                "algo_dir": str(algo_dir),
                "data_path": str(data_path),
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
                    error_message=(
                        f"Evaluation timed out after {cfg.timeout}s"
                    ),
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

            # Step 4: Parse subprocess output
            try:
                result = json.loads(stdout_text.strip())
            except json.JSONDecodeError:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=(
                        f"Invalid JSON output: {stdout_text[:200]}"
                    ),
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

            # Step 5: Compute score (negate because we minimize tour_length)
            tour_length = result.get("tour_length", float("inf"))
            exec_time = result.get("execution_time_ms", duration_ms)
            score = -tour_length

            metrics_dict = {
                "tour_length": tour_length,
            }

            # Step 6: Build BehaviorData
            behavior = None
            behavior_storage = cfg.behavior_storage
            instance_name = Path(data_path).stem

            if behavior_storage != "none":
                edge_lengths = result.get("edge_lengths", [])
                longest_edge = max(edge_lengths) if edge_lengths else 0.0
                mean_edge = (
                    sum(edge_lengths) / len(edge_lengths)
                    if edge_lengths
                    else 0.0
                )

                obs_text = _build_observation_text(
                    instance_name=instance_name,
                    tour_length=tour_length,
                    n_cities=result.get("n_cities", 0),
                    execution_time_ms=exec_time,
                    longest_edge=longest_edge,
                    mean_edge=mean_edge,
                )

                viz = None
                if behavior_storage == "rendered":
                    image_b64 = result.get("image_base64")
                    if image_b64:
                        viz = BehaviorVisualization(
                            label="TSP Tour Map",
                            media_type="image/png",
                            data_base64=image_b64,
                        )
                elif behavior_storage == "raw":
                    viz = BehaviorVisualization(
                        label="TSP Tour Map",
                        media_type="image/png",
                        raw_data={
                            "nodes": result.get("nodes", []),
                            "tour": result.get("tour", []),
                            "tour_length": tour_length,
                            "edge_lengths": edge_lengths,
                        },
                        renderer="tsp_tour",
                    )

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
    """Run a single TSP evaluation in an isolated subprocess."""
    if len(sys.argv) < 2:
        print(
            "Usage: python tsp_multimodal_evaluator.py '<json>'",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    algo_dir = Path(input_data["algo_dir"])
    data_path = Path(input_data["data_path"])
    behavior_storage = input_data.get("behavior_storage", "rendered")

    # Load data
    with open(data_path, encoding="utf-8") as f:
        test_data = json.load(f)

    nodes = test_data.get("nodes", [])
    if not nodes:
        print(json.dumps({"error": "No nodes in data file"}))
        return

    evaluator = TSPMultimodalEvaluator()

    try:
        mod = evaluator._load_algorithm_module(algo_dir)

        # The algorithm file exposes solve() which wraps the evolved function
        if hasattr(mod, "solve"):
            algo_input = {"nodes": nodes}
            start_time = time.time()
            try:
                solve_result = mod.solve(algo_input)
            except Exception as e:
                print(json.dumps({"error": f"Algorithm failed: {e}"}))
                return
            execution_time_ms = (time.time() - start_time) * 1000

            # solve() returns {"result": tour_list}
            if isinstance(solve_result, dict):
                tour = solve_result.get(
                    "result", solve_result.get("tour", [])
                )
            else:
                tour = list(solve_result)

        elif hasattr(mod, "hybrid_kdtree_two_phase_tsp"):
            start_time = time.time()
            try:
                tour = mod.hybrid_kdtree_two_phase_tsp(nodes)
            except Exception as e:
                print(json.dumps({"error": f"Algorithm failed: {e}"}))
                return
            execution_time_ms = (time.time() - start_time) * 1000
        else:
            print(json.dumps({
                "error": "Neither solve nor hybrid_kdtree_two_phase_tsp found",
            }))
            return

        # Validate tour
        nodes_arr = np.array(nodes, dtype=np.float64)
        n = len(nodes_arr)

        if not isinstance(tour, (list, tuple)) or len(tour) == 0:
            print(json.dumps({"error": "Empty or invalid tour"}))
            return

        tour = [int(x) for x in tour]

        if len(tour) != n:
            print(json.dumps({
                "error": f"Tour has {len(tour)} cities, expected {n}",
            }))
            return

        tour_set = set(tour)
        if (
            len(tour_set) != n
            or min(tour_set) != 0
            or max(tour_set) != n - 1
        ):
            print(json.dumps({
                "error": "Tour does not visit each city exactly once",
            }))
            return

        # Compute tour length and edge lengths
        edge_lengths = []
        tour_length = 0.0
        for i in range(n):
            src = tour[i]
            dst = tour[(i + 1) % n]
            dx = nodes_arr[src, 0] - nodes_arr[dst, 0]
            dy = nodes_arr[src, 1] - nodes_arr[dst, 1]
            dist = math.sqrt(dx * dx + dy * dy)
            edge_lengths.append(dist)
            tour_length += dist

        result = {
            "tour": tour,
            "tour_length": tour_length,
            "edge_lengths": edge_lengths,
            "execution_time_ms": execution_time_ms,
            "n_cities": n,
        }

        # Handle behavior_storage modes
        if behavior_storage == "rendered":
            result["image_base64"] = _render_result_image(
                nodes=nodes,
                tour=tour,
                tour_length=tour_length,
                edge_lengths=edge_lengths,
            )
            # Don't send large data over pipe in rendered mode
            result.pop("edge_lengths", None)
        elif behavior_storage == "raw":
            # Include nodes for deferred rendering
            result["nodes"] = nodes
        elif behavior_storage == "none":
            result.pop("edge_lengths", None)

    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()