"""Multimodal evaluator for CVRP greedy route-construction task.

Evaluates LLM-evolved select_next_node heuristics by running the full
route-construction driver in a subprocess, computing normalized gap to
baseline, and generating route visualizations for multimodal feedback.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, List

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
    coordinates: list[list[float]],
    route: list[int],
    demands: list[int],
    vehicle_capacity: int,
    total_cost: float,
    baseline_cost: float,
) -> str:
    """Render CVRP solution as a base64 PNG with colored routes.

    Each vehicle trip (depot -> customers -> depot) is drawn in a distinct
    color. The depot is highlighted as a red square, customer nodes show
    their demand, and the title summarizes cost vs baseline.

    Args:
        coordinates: List of [x, y] for all nodes (index 0 = depot).
        route: Full ordered node sequence including depot returns.
        demands: Demand per node (depot = 0).
        vehicle_capacity: Max capacity per vehicle.
        total_cost: Total Euclidean distance of the solution.
        baseline_cost: Known baseline/optimal cost.

    Returns:
        Base64-encoded PNG string.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    coords = np.array(coordinates, dtype=float)
    fig, ax = plt.subplots(figsize=(8, 8))

    # Split route into individual vehicle trips
    trips: list[list[int]] = []
    current_trip: list[int] = []
    for node in route:
        if node == 0:
            if current_trip:
                trips.append([0] + current_trip + [0])
                current_trip = []
        else:
            current_trip.append(node)
    if current_trip:
        trips.append([0] + current_trip + [0])

    # Color palette for routes
    n_trips = max(len(trips), 1)
    cmap = cm.get_cmap("tab10" if n_trips <= 10 else "tab20", n_trips)

    for i, trip in enumerate(trips):
        color = cmap(i)
        trip_coords = coords[trip]
        load = sum(demands[n] for n in trip if n != 0)
        label = f"Route {i+1} (load={int(load)}/{vehicle_capacity})"
        ax.plot(
            trip_coords[:, 0], trip_coords[:, 1],
            "o-", color=color, markersize=4, linewidth=1.2,
            alpha=0.8, label=label,
        )

    # Plot customer nodes with demand labels
    for idx in range(1, len(coords)):
        ax.annotate(
            f"{int(demands[idx])}",
            (coords[idx, 0], coords[idx, 1]),
            textcoords="offset points", xytext=(4, 4),
            fontsize=6, color="gray",
        )

    # Highlight depot
    ax.scatter(
        [coords[0, 0]], [coords[0, 1]],
        s=200, marker="s", c="red", edgecolors="darkred",
        linewidths=2, zorder=10, label="Depot",
    )

    gap_pct = ((total_cost - baseline_cost) / baseline_cost) * 100 if baseline_cost > 0 else 0
    ax.set_title(
        f"CVRP Solution — {n_trips} vehicles\n"
        f"Cost: {total_cost:.1f} | Baseline: {baseline_cost:.1f} | "
        f"Gap: {gap_pct:+.2f}%",
        fontsize=10,
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    if n_trips <= 10:
        ax.legend(loc="upper right", fontsize=6, ncol=1)

    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _build_observation_text(
    instance_name: str,
    total_cost: float,
    baseline_cost: float,
    n_vehicles: int,
    n_customers: int,
    vehicle_capacity: int,
    execution_time_ms: float,
) -> str:
    """Build LLM-readable observation text summarizing the CVRP result.

    Args:
        instance_name: Name of the data instance.
        total_cost: Total route distance.
        baseline_cost: Known baseline/optimal cost.
        n_vehicles: Number of vehicle trips used.
        n_customers: Number of customer nodes.
        vehicle_capacity: Vehicle capacity.
        execution_time_ms: Execution time.

    Returns:
        Compact pipe-separated observation string.
    """
    if baseline_cost > 0:
        gap_pct = ((total_cost - baseline_cost) / baseline_cost) * 100
        norm_gap = -(total_cost - baseline_cost) / baseline_cost
    else:
        gap_pct = 0.0
        norm_gap = 0.0

    return (
        f"{instance_name} | Customers={n_customers} | Cap={vehicle_capacity} | "
        f"Vehicles={n_vehicles} | Cost={total_cost:.2f} | "
        f"Baseline={baseline_cost:.2f} | Gap={gap_pct:+.2f}% | "
        f"NormGap={norm_gap:.4f} | Time={execution_time_ms:.1f}ms"
    )


# ===========================================================================
# Deferred renderer (for raw mode)
# ===========================================================================


@BaseRenderer.register("cvrp_solution")
class CVRPSolutionRenderer(BaseRenderer):
    """Deferred renderer for CVRP solution visualizations.

    Converts compact raw data (coordinates, route, demands) into an
    annotated route map PNG on demand.
    """

    def render(self, raw_data: dict[str, Any], **kwargs: Any) -> str:
        """Render raw CVRP data to a base64 PNG.

        Args:
            raw_data: Dict with coordinates, route, demands,
                vehicle_capacity, total_cost, baseline_cost.

        Returns:
            Base64-encoded PNG string.
        """
        return _render_result_image(
            coordinates=raw_data["coordinates"],
            route=raw_data["route"],
            demands=raw_data["demands"],
            vehicle_capacity=raw_data["vehicle_capacity"],
            total_cost=raw_data["total_cost"],
            baseline_cost=raw_data["baseline_cost"],
        )


# ===========================================================================
# Evaluator class
# ===========================================================================


@BaseEvaluator.register("cvrp_multimodal_evaluator")
class CVRPMultimodalEvaluator(BaseEvaluator):
    """Multimodal evaluator for CVRP greedy route-construction.

    Runs the algorithm driver (evaluation.py) in a subprocess, computes
    normalized gap to baseline, and generates route visualizations.
    """

    def __init__(self):
        """Initialize evaluator with metric definitions."""
        self._metrics = [
            Metric(
                name="normalized_gap",
                type=MetricType.MAXIMIZE,
                weight=1.0,
                description=(
                    "Negative normalized gap to baseline: "
                    "-(LLM_distance - baseline) / baseline. "
                    "Higher (closer to 0) is better."
                ),
            ),
        ]

    @property
    def name(self) -> str:
        return "cvrp_multimodal_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return self._metrics

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate a CVRP algorithm via subprocess isolation.

        Spawns evaluation.py as a subprocess, parses the JSON result,
        computes normalized gap, and builds BehaviorData.

        Args:
            cfg: EvalContext with project_root, data_path, timeout,
                and behavior_storage.

        Returns:
            EvaluationResult with score, metrics, and behavior data.
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

            # --- Step 2: Find algorithm file (worktree-compatible) ---
            algo_file = project_root / "algorithm" / "evaluation.py"
            if not algo_file.exists():
                # Flat worktree layout
                algo_file = project_root / "evaluation.py"
                if not algo_file.exists():
                    return EvaluationResult(
                        score=0.0,
                        metrics={},
                        success=False,
                        error_message=(
                            f"evaluation.py not found in "
                            f"{project_root / 'algorithm'} or {project_root}"
                        ),
                        duration_ms=(time.time() - start_time) * 1000,
                    )

            # --- Step 3: Spawn subprocess ---
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(algo_file), str(data_path),
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
                    error_message=f"Timed out after {cfg.timeout}s",
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

            # --- Step 4: Parse subprocess output ---
            try:
                result = json.loads(stdout_text.strip())
            except json.JSONDecodeError:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Invalid JSON: {stdout_text[:300]}",
                    duration_ms=duration_ms,
                )

            total_cost = result.get("total_cost", float("inf"))
            route = result.get("routes", [])

            if math.isinf(total_cost) or not route:
                return EvaluationResult(
                    score=0.0,
                    metrics={"normalized_gap": -1.0},
                    success=False,
                    error_message="Algorithm produced no valid route",
                    duration_ms=duration_ms,
                )

            # --- Step 5: Compute score ---
            # Load instance data for baseline and visualization
            with open(data_path, "r", encoding="utf-8") as f:
                instance_data = json.load(f)

            baseline_cost = float(instance_data.get("label", total_cost))
            if baseline_cost <= 0:
                baseline_cost = total_cost

            normalized_gap = -(total_cost - baseline_cost) / baseline_cost
            score = normalized_gap

            metrics_dict = {
                "normalized_gap": normalized_gap,
            }

            # --- Step 6: Build BehaviorData ---
            behavior = None
            behavior_storage = cfg.behavior_storage
            instance_name = data_path.stem

            coordinates = instance_data.get("coordinates", [])
            demands = instance_data.get("demands", [])
            capacity = int(instance_data.get("capacity", 0))

            # Count vehicle trips
            n_vehicles = max(sum(1 for n in route if n == 0) - 1, 1)
            n_customers = len(demands) - 1 if demands else 0

            if behavior_storage != "none":
                obs_text = _build_observation_text(
                    instance_name=instance_name,
                    total_cost=total_cost,
                    baseline_cost=baseline_cost,
                    n_vehicles=n_vehicles,
                    n_customers=n_customers,
                    vehicle_capacity=capacity,
                    execution_time_ms=duration_ms,
                )

                viz = None
                if behavior_storage == "rendered":
                    try:
                        image_b64 = _render_result_image(
                            coordinates=coordinates,
                            route=route,
                            demands=[int(d) for d in demands],
                            vehicle_capacity=capacity,
                            total_cost=total_cost,
                            baseline_cost=baseline_cost,
                        )
                        viz = BehaviorVisualization(
                            label="CVRP Solution Routes",
                            media_type="image/png",
                            data_base64=image_b64,
                        )
                    except Exception:
                        pass  # Visualization failure is non-fatal

                elif behavior_storage == "raw":
                    viz = BehaviorVisualization(
                        label="CVRP Solution Routes",
                        media_type="image/png",
                        raw_data={
                            "coordinates": coordinates,
                            "route": route,
                            "demands": [int(d) for d in demands],
                            "vehicle_capacity": capacity,
                            "total_cost": total_cost,
                            "baseline_cost": baseline_cost,
                        },
                        renderer="cvrp_solution",
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
                    "total_cost": total_cost,
                    "baseline_cost": baseline_cost,
                    "n_vehicles": n_vehicles,
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