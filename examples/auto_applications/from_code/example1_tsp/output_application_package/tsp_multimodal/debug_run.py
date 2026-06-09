#!/usr/bin/env python3
"""Debug runner for TSP multimodal algorithm.

Creates a small sample input, runs the algorithm directly (no subprocess),
and prints the result for quick validation.
"""

import math
import sys
from pathlib import Path

# Add algorithm directory to path
algo_dir = Path(__file__).resolve().parent / "algorithm"
if algo_dir.exists():
    sys.path.insert(0, str(algo_dir))
else:
    # Worktree layout: solve.py is in the same directory
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from solve import hybrid_kdtree_two_phase_tsp


def main():
    # Small 10-city instance arranged roughly in a circle + some interior
    nodes = [
        [0.0, 0.0],
        [10.0, 0.0],
        [20.0, 5.0],
        [20.0, 15.0],
        [15.0, 20.0],
        [5.0, 20.0],
        [0.0, 15.0],
        [0.0, 5.0],
        [10.0, 10.0],
        [8.0, 5.0],
    ]

    n = len(nodes)
    print(f"Running TSP on {n} cities...")
    print(f"Cities: {nodes}")
    print()

    tour = hybrid_kdtree_two_phase_tsp(nodes)

    print(f"Tour: {tour}")
    print(f"Tour length (cities): {len(tour)}")

    # Validate
    if len(tour) != n:
        print(f"[FAIL] Expected {n} cities in tour, got {len(tour)}")
        return

    if set(tour) != set(range(n)):
        print("[FAIL] Tour does not visit each city exactly once")
        return

    # Compute tour length
    tour_length = 0.0
    edge_lengths = []
    for i in range(n):
        src = tour[i]
        dst = tour[(i + 1) % n]
        dx = nodes[src][0] - nodes[dst][0]
        dy = nodes[src][1] - nodes[dst][1]
        dist = math.sqrt(dx * dx + dy * dy)
        edge_lengths.append(dist)
        tour_length += dist

    print(f"Tour length: {tour_length:.2f}")
    print(f"Edge lengths: {[f'{e:.2f}' for e in edge_lengths]}")
    print(f"Longest edge: {max(edge_lengths):.2f}")
    print(f"Mean edge: {sum(edge_lengths)/len(edge_lengths):.2f}")
    print()
    print("[PASS] Algorithm ran successfully")


if __name__ == "__main__":
    main()