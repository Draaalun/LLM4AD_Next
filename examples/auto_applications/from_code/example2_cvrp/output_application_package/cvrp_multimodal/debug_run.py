"""Quick debug runner for the CVRP algorithm.

Constructs a small CVRP instance, runs the driver's process() directly
(no subprocess), and prints the result for validation.
"""

from __future__ import annotations

import sys
import json
import copy
import numpy as np
from pathlib import Path

# Add algorithm directory to path so we can import evaluation.py
sys.path.insert(0, str(Path(__file__).parent / "algorithm"))
from evaluation import select_next_node, tour_cost, route_construct, process


def make_sample_instance() -> dict:
    """Create a small 10-customer CVRP instance for debugging."""
    # Depot at (50, 50), 10 customers arranged around it
    coords = [
        [50.0, 50.0],   # 0: depot
        [20.0, 70.0],   # 1
        [30.0, 80.0],   # 2
        [80.0, 70.0],   # 3
        [75.0, 85.0],   # 4
        [25.0, 30.0],   # 5
        [35.0, 20.0],   # 6
        [70.0, 25.0],   # 7
        [65.0, 35.0],   # 8
        [50.0, 90.0],   # 9
        [55.0, 15.0],   # 10
    ]
    n = len(coords)
    coordinates = np.array(coords, dtype=float)

    # Build distance matrix
    distances = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            distances[i][j] = np.linalg.norm(coordinates[i] - coordinates[j])

    demands = [0, 10, 15, 10, 20, 15, 10, 20, 15, 10, 5]
    capacity = 50
    baseline = 350.0  # approximate baseline

    return {
        "coordinates": coords,
        "distances": distances.tolist(),
        "demands": demands,
        "capacity": capacity,
        "label": baseline,
    }


def main():
    instance = make_sample_instance()
    print(f"Instance: {len(instance['demands']) - 1} customers, capacity={instance['capacity']}")
    print(f"Baseline cost: {instance['label']}")
    print()

    result = process(instance)

    route = result["routes"]
    total_cost = result["total_cost"]

    print(f"Route: {route}")
    print(f"Total cost: {total_cost:.2f}")

    if route:
        # Count vehicles
        n_vehicles = max(sum(1 for n in route if n == 0) - 1, 1)
        print(f"Vehicles used: {n_vehicles}")

        # Verify all customers visited
        visited = set(n for n in route if n != 0)
        expected = set(range(1, len(instance["demands"])))
        if visited == expected:
            print("All customers visited: OK")
        else:
            missing = expected - visited
            print(f"MISSING customers: {missing}")

        # Verify capacity constraints
        demands = instance["demands"]
        cap = instance["capacity"]
        trips = []
        current_trip = []
        for node in route:
            if node == 0:
                if current_trip:
                    trips.append(current_trip)
                    current_trip = []
            else:
                current_trip.append(node)
        if current_trip:
            trips.append(current_trip)

        capacity_ok = True
        for i, trip in enumerate(trips):
            load = sum(demands[n] for n in trip)
            status = "OK" if load <= cap else "OVER"
            if load > cap:
                capacity_ok = False
            print(f"  Trip {i+1}: {trip} load={load}/{cap} [{status}]")

        if capacity_ok:
            print("Capacity constraints: OK")
        else:
            print("Capacity constraints: VIOLATED")

        # Normalized gap
        baseline = instance["label"]
        if baseline > 0:
            norm_gap = -(total_cost - baseline) / baseline
            print(f"Normalized gap: {norm_gap:.4f}")
    else:
        print("No valid route produced!")


if __name__ == "__main__":
    main()