"""Multimodal evaluator for CVRP algorithm evolution in LLM4AD.

Evaluates evolved solve_cvrp heuristics by running them in a subprocess,
computing distance/feasibility metrics, and generating route map visualizations
that help the LLM diagnose route structure issues.
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
    demands: list[int],
    capacity: int,
    routes: list[list[int]],
    total_distance: float,
    num_routes: int,
    route_loads: list[int],
) -> str:
    """Render CVRP solution as a base64 PNG route map.

    Draws the depot as a red square, customers as blue circles annotated
    with demand values, and each route as a differently colored path.
    The title shows total distance and number of routes.

    Args:
        nodes: List of [x, y] coordinates; index 0 is the depot.
        demands: Demand per node; index 0 is 0.
        capacity: Vehicle capacity Q.
        routes: List of routes, each a list of node indices starting/ending with 0.
        total_distance: Total Euclidean distance across all routes.
        num_routes: Number of vehicle routes.
        route_loads: Total demand served by each route.

    Returns:
        Base64-encoded PNG string.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    fig, ax = plt.subplots(figsize=(10, 8))

    nodes_arr = np.array(nodes)

    # Draw customer nodes
    if len(nodes_arr) > 1:
        ax.scatter(
            nodes_arr[1:, 0], nodes_arr[1:, 1],
            c="#3b82f6", s=60, zorder=3, edgecolors="#1e3a5f",
            linewidths=0.8, label="Customers",
        )
        # Annotate customers with demand values
        for i in range(1, len(nodes_arr)):
            ax.annotate(
                str(demands[i]),
                (nodes_arr[i, 0], nodes_arr[i, 1]),
                textcoords="offset points", xytext=(5, 5),
                fontsize=7, color="#374151",
            )

    # Draw depot
    ax.scatter(
        [nodes_arr[0, 0]], [nodes_arr[0, 1]],
        c="#ef4444", s=150, marker="s", zorder=5,
        edgecolors="#7f1d1d", linewidths=1.5, label="Depot",
    )

    # Draw routes with distinct colors
    if routes:
        cmap = cm.get_cmap("tab10", max(len(routes), 1))
        for r_idx, route in enumerate(routes):
            color = cmap(r_idx % 10)
            route_coords = [nodes_arr[node_id] for node_id in route]
            if len(route_coords) < 2:
                continue
            route_coords = np.array(route_coords)
            load = route_loads[r_idx] if r_idx < len(route_loads) else 0
            ax.plot(
                route_coords[:, 0], route_coords[:, 1],
                "-o", color=color, markersize=3, linewidth=1.2,
                alpha=0.8, label=f"Route {r_idx + 1} (load={load}/{capacity})",
            )

    # Axis labels and title
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(
        f"CVRP Solution: {num_routes} routes, "
        f"Total Distance = {total_distance:.2f}",
        fontsize=12,
    )

    # Legend: limit entries if many routes
    handles, labels = ax.get_legend_handles_labels()
    max_legend = 12
    if len(handles) > max_legend:
        handles = handles[:max_legend]
        labels = labels[:max_legend]
        labels[-1] = f"... and {num_routes - max_legend + 2} more routes"
    ax.legend(handles, labels, loc="upper right", fontsize=7)

    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _build_observation_text(
    instance_name: str,
    total_distance: float,
    num_routes: int,
    feasibility_penalty: float,
    num_customers: int,
    capacity: int,
    execution_time_ms: float,
) -> str:
    """Build LLM-readable observation text summarizing the CVRP result.

    Args:
        instance_name: Name of the data instance.
        total_distance: Total Euclidean distance of all routes.
        num_routes: Number of vehicle routes used.
        feasibility_penalty: Penalty for constraint violations (0 = feasible).
        num_customers: Number of customers served.
        capacity: Vehicle capacity Q.
        execution_time_ms: Algorithm execution time.

    Returns:
        Formatted observation string.
    """
    feasible_str = "FEASIBLE" if feasibility_penalty == 0.0 else f"INFEASIBLE(pen={feasibility_penalty:.1f})"
    return (
        f"{instance_name} | Dist={total_distance:.2f} | Routes={num_routes} | "
        f"{feasible_str} | Customers={num_customers} | Q={capacity} | "
        f"Time={execution_time_ms:.1f}ms"
    )


# ===========================================================================
# Deferred renderer (for raw mode)
# ===========================================================================


@BaseRenderer.register("cvrp_route_map")
class CVRPRouteMapRenderer(BaseRenderer):
    """Deferred renderer for CVRP route map visualization.

    Converts compact raw data (nodes, routes, demands) into an annotated
    2D route map PNG on demand.
    """

    def render(self, raw_data: dict[str, Any], **kwargs: Any) -> str:
        """Render raw CVRP data to an annotated base64 PNG.

        Args:
            raw_data: Dict with nodes, demands, capacity, routes, etc.
            **kwargs: Unused.

        Returns:
            Base64-encoded PNG string.
        """
        return _render_result_image(
            nodes=raw_data["nodes"],
            demands=raw_data["demands"],
            capacity=raw_data["capacity"],
            routes=raw_data.get("routes", []),
            total_distance=raw_data.get("total_distance", 0.0),
            num_routes=raw_data.get("num_routes", 0),
            route_loads=raw_data.get("route_loads", []),
        )


# ===========================================================================
# Helper: Euclidean distance
# ===========================================================================


def _euclidean(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


# ===========================================================================
# Evaluator class
# ===========================================================================


@BaseEvaluator.register("cvrp_algorithm_evolution_evaluator")
class CVRPAlgorithmEvolutionEvaluatorMultimodal(BaseEvaluator):
    """Multimodal evaluator for CVRP algorithm evolution.

    Runs evolved solve_cvrp heuristics in a subprocess, validates routes,
    computes distance/feasibility metrics, and builds BehaviorData with
    route map visualizations.
    """

    def __init__(self):
        """Initialize evaluator with CVRP metric definitions."""
        self._metrics = [
            Metric(
                name="total_distance",
                type=MetricType.MINIMIZE,
                weight=0.8,
                description="Total Euclidean distance traveled across all vehicle routes.",
            ),
            Metric(
                name="num_routes",
                type=MetricType.MINIMIZE,
                weight=0.15,
                description="Number of vehicles (routes) used.",
            ),
            Metric(
                name="feasibility_penalty",
                type=MetricType.MINIMIZE,
                weight=0.05,
                description="Penalty for constraint violations (0 = feasible).",
            ),
        ]

    @property
    def name(self) -> str:
        return "cvrp_algorithm_evolution_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return self._metrics

    # ------------------------------------------------------------------
    # Algorithm loading
    # ------------------------------------------------------------------

    def _load_algorithm_module(self, algo_dir: Path):
        """Load the cvrp_solver module from the given directory.

        Args:
            algo_dir: Path to directory containing cvrp_solver.py.

        Returns:
            The loaded module with a solve_cvrp function.
        """
        module_file = algo_dir / "cvrp_solver.py"
        if not module_file.exists():
            raise FileNotFoundError(f"cvrp_solver.py not found in {algo_dir}")

        module_name = f"_algo_{id(self)}_{hash(str(module_file))}"
        spec = importlib.util.spec_from_file_location(module_name, str(module_file))
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
        nodes: list,
        demands: list[int],
        capacity: int,
    ) -> dict:
        """Run solve_cvrp and validate the result.

        Args:
            algo_func: The solve_cvrp function.
            nodes: List of (x, y) tuples.
            demands: Demand per node.
            capacity: Vehicle capacity Q.

        Returns:
            Dict with metrics and raw behavior data, or an error key.
        """
        start_time = time.time()

        try:
            result = algo_func(nodes, demands, capacity)
        except Exception as e:
            return {"error": f"Algorithm execution failed: {e}"}

        execution_time_ms = (time.time() - start_time) * 1000

        if not isinstance(result, dict):
            return {"error": f"Algorithm must return a dict, got {type(result).__name__}"}

        routes = result.get("routes", [])
        reported_distance = result.get("total_distance", None)
        metadata = result.get("metadata", {})

        if not isinstance(routes, list):
            return {"error": f"'routes' must be a list, got {type(routes).__name__}"}

        # --- Validate routes and compute metrics ---
        num_customers = len(nodes) - 1
        visited = set()
        feasibility_penalty = 0.0
        computed_distance = 0.0
        route_loads = []

        for r_idx, route in enumerate(routes):
            if not isinstance(route, list) or len(route) < 2:
                feasibility_penalty += 100.0
                route_loads.append(0)
                continue

            if route[0] != 0 or route[-1] != 0:
                feasibility_penalty += 50.0

            route_load = 0
            for i in range(len(route) - 1):
                n1, n2 = route[i], route[i + 1]
                if n1 < 0 or n1 >= len(nodes) or n2 < 0 or n2 >= len(nodes):
                    feasibility_penalty += 100.0
                    continue
                computed_distance += _euclidean(nodes[n1], nodes[n2])

            for node_id in route:
                if node_id == 0:
                    continue
                if node_id < 0 or node_id >= len(nodes):
                    feasibility_penalty += 100.0
                    continue
                if node_id in visited:
                    feasibility_penalty += 50.0
                visited.add(node_id)
                route_load += demands[node_id]

            if route_load > capacity:
                feasibility_penalty += (route_load - capacity) * 10.0

            route_loads.append(route_load)

        # Check for unvisited customers
        all_customers = set(range(1, len(nodes)))
        unvisited = all_customers - visited
        feasibility_penalty += len(unvisited) * 100.0

        total_distance = computed_distance
        num_routes = len(routes)

        return {
            "total_distance": total_distance,
            "num_routes": num_routes,
            "feasibility_penalty": feasibility_penalty,
            "execution_time_ms": execution_time_ms,
            "routes": routes,
            "route_loads": route_loads,
            "num_customers": num_customers,
            "metadata": metadata,
        }

    # ------------------------------------------------------------------
    # Main evaluate method
    # ------------------------------------------------------------------

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate a solve_cvrp implementation via subprocess.

        Args:
            cfg: EvalContext with project_root, data_path, timeout,
                 behavior_storage.

        Returns:
            EvaluationResult with score, metrics, and behavior data.
        """
        start_time = time.time()

        try:
            project_root = Path(str(cfg.project_root))
            data_path = Path(str(cfg.data_path))

            # Step 1: Validate data file
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0, metrics={}, success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Step 2: Find algorithm directory (worktree-compatible)
            algo_dir = project_root / "cvrp_solver_algorithm"
            if not algo_dir.exists():
                if (project_root / "cvrp_solver.py").exists():
                    algo_dir = project_root
                else:
                    return EvaluationResult(
                        score=0.0, metrics={}, success=False,
                        error_message=f"Algorithm not found in {project_root}",
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
                    score=0.0, metrics={}, success=False,
                    error_message=f"Evaluation timed out after {cfg.timeout}s",
                    duration_ms=cfg.timeout * 1000,
                )

            duration_ms = (time.time() - start_time) * 1000
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return EvaluationResult(
                    score=0.0, metrics={}, success=False,
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
                    score=0.0, metrics={}, success=False,
                    error_message=f"Invalid JSON output: {stdout_text[:200]}",
                    duration_ms=duration_ms,
                )

            if "error" in result:
                return EvaluationResult(
                    score=0.0, metrics={}, success=False,
                    error_message=result["error"],
                    duration_ms=duration_ms,
                )

            # Step 5: Compute score (higher is better for evolution)
            total_distance = result.get("total_distance", float("inf"))
            num_routes = result.get("num_routes", 100)
            feasibility_penalty = result.get("feasibility_penalty", 0.0)
            exec_time = result.get("execution_time_ms", duration_ms)

            # Weighted negative score (all metrics are minimized)
            score = -(
                0.8 * total_distance
                + 0.15 * num_routes * 100.0
                + 0.05 * feasibility_penalty * 100.0
            )

            metrics_dict = {
                "total_distance": total_distance,
                "num_routes": num_routes,
                "feasibility_penalty": feasibility_penalty,
            }

            # Step 6: Build BehaviorData
            behavior = None
            behavior_storage = cfg.behavior_storage
            instance_name = Path(str(data_path)).stem

            if behavior_storage != "none":
                obs_text = _build_observation_text(
                    instance_name=instance_name,
                    total_distance=total_distance,
                    num_routes=num_routes,
                    feasibility_penalty=feasibility_penalty,
                    num_customers=result.get("num_customers", 0),
                    capacity=result.get("capacity", 0),
                    execution_time_ms=exec_time,
                )

                viz = None
                if behavior_storage == "rendered":
                    image_b64 = result.get("image_base64")
                    if image_b64:
                        viz = BehaviorVisualization(
                            label="CVRP Route Map",
                            media_type="image/png",
                            data_base64=image_b64,
                        )
                elif behavior_storage == "raw":
                    viz = BehaviorVisualization(
                        label="CVRP Route Map",
                        media_type="image/png",
                        raw_data={
                            "nodes": result.get("nodes", []),
                            "demands": result.get("demands", []),
                            "capacity": result.get("capacity", 0),
                            "routes": result.get("routes", []),
                            "total_distance": total_distance,
                            "num_routes": num_routes,
                            "route_loads": result.get("route_loads", []),
                        },
                        renderer="cvrp_route_map",
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
                score=0.0, metrics={}, success=False,
                error_message=f"Evaluation error: {e}",
                duration_ms=(time.time() - start_time) * 1000,
            )


# ---------------------------------------------------------------------------
# Subprocess entry point
# ---------------------------------------------------------------------------


def _subprocess_main() -> None:
    """Run a single CVRP evaluation in an isolated subprocess."""
    if len(sys.argv) < 2:
        print("Usage: python cvrp_evaluator.py '<json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    algo_dir = Path(input_data["algo_dir"])
    data_path = Path(input_data["data_path"])
    behavior_storage = input_data.get("behavior_storage", "rendered")

    # Load instance data
    with open(data_path, encoding="utf-8") as f:
        test_data = json.load(f)

    nodes = [tuple(n) for n in test_data["nodes"]]
    demands = test_data["demands"]
    capacity = test_data["capacity"]

    evaluator = CVRPAlgorithmEvolutionEvaluatorMultimodal()

    try:
        mod = evaluator._load_algorithm_module(algo_dir)
        if not hasattr(mod, "solve_cvrp"):
            result = {"error": "solve_cvrp function not found in module"}
        else:
            result = evaluator._run_algorithm(
                mod.solve_cvrp, nodes, demands, capacity,
            )

            if "error" not in result:
                # Attach instance data needed for visualization
                result["capacity"] = capacity
                result["num_customers"] = len(nodes) - 1

                if behavior_storage == "rendered":
                    nodes_list = [list(n) for n in nodes]
                    result["image_base64"] = _render_result_image(
                        nodes=nodes_list,
                        demands=demands,
                        capacity=capacity,
                        routes=result.get("routes", []),
                        total_distance=result.get("total_distance", 0.0),
                        num_routes=result.get("num_routes", 0),
                        route_loads=result.get("route_loads", []),
                    )
                    # Don't send large route data in rendered mode
                    result.pop("routes", None)
                    result.pop("route_loads", None)
                elif behavior_storage == "raw":
                    result["nodes"] = [list(n) for n in nodes]
                    result["demands"] = demands
                elif behavior_storage == "none":
                    result.pop("routes", None)
                    result.pop("route_loads", None)

    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()