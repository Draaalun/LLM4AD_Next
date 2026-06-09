#!/usr/bin/env python3
"""Debug runner for the CVRP solver algorithm.

Creates a small sample CVRP instance and runs solve_cvrp directly
(no subprocess) for quick validation and debugging.
"""

import json
import sys
from pathlib import Path

# Add algorithm directory to path
algo_dir = Path(__file__).parent / "cvrp_solver_algorithm"
if algo_dir.exists():
    sys.path.insert(0, str(algo_dir))
else:
    sys.path.insert(0, str(Path(__file__).parent))

from cvrp_solver import solve_cvrp


def main():
    # Small CVRP instance: 1 depot + 6 customers
    nodes = [
        (50.0, 50.0),   # 0: depot
        (20.0, 70.0),   # 1
        (30.0, 30.0),   # 2
        (80.0, 60.0),   # 3
        (70.0, 20.0),   # 4
        (10.0, 50.0),   # 5
        (60.0, 80.0),   # 6
    ]
    demands = [0, 10, 15, 20, 10, 5, 15]
    capacity = 30

    print("=" * 60)
    print("CVRP Debug Run")
    print("=" * 60)
    print(f"Nodes: {len(nodes)} (1 depot + {len(nodes) - 1} customers)")
    print(f"Demands: {demands}")
    print(f"Capacity: {capacity}")
    print(f"Total demand: {sum(demands)}")
    print()

    result = solve_cvrp(nodes, demands, capacity)

    print("Result:")
    print(f"  Total distance: {result['total_distance']:.2f}")
    print(f"  Number of routes: {len(result['routes'])}")
    print(f"  Metadata: {result.get('metadata', {})}")
    print()

    for i, route in enumerate(result["routes"]):
        route_demand = sum(demands[n] for n in route if n != 0)
        print(f"  Route {i + 1}: {route}  (load={route_demand}/{capacity})")

    # Basic validation
    print()
    all_customers = set(range(1, len(nodes)))
    visited = set()
    for route in result["routes"]:
        assert route[0] == 0, f"Route must start at depot: {route}"
        assert route[-1] == 0, f"Route must end at depot: {route}"
        for n in route:
            if n != 0:
                visited.add(n)

    missing = all_customers - visited
    if missing:
        print(f"[WARN] Unvisited customers: {missing}")
    else:
        print("[OK] All customers visited")

    duplicates = []
    seen = set()
    for route in result["routes"]:
        for n in route:
            if n != 0:
                if n in seen:
                    duplicates.append(n)
                seen.add(n)
    if duplicates:
        print(f"[WARN] Duplicate visits: {duplicates}")
    else:
        print("[OK] No duplicate visits")

    print()
    print("Debug run complete.")


if __name__ == "__main__":
    main()