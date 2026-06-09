#!/usr/bin/env python3
"""Traveling Salesman Problem (TSP) solver with EVOLVE markers for LLM4AD optimization.

This is a baseline Nearest Neighbor implementation that will be evolved
by the LLM4AD system to find better TSP tours.
"""

import json
import sys

import numpy as np


# EVOLVE_START
def nearest_neighbor_tsp(nodes):
    """Solve TSP using Nearest Neighbor heuristic.

    Args:
        nodes: List of (x, y) coordinate tuples representing cities

    Returns:
        list: Tour as a list of node indices in visitation order
    """
    n = len(nodes)
    if n == 0:
        return []
    if n == 1:
        return [0]

    nodes_array = np.array(nodes, dtype=np.float64)
    unvisited = set(range(1, n))
    tour = [0]
    current = 0

    while unvisited:
        current_pos = nodes_array[current]
        best_dist = float("inf")
        best_next = -1

        for idx in unvisited:
            dist = np.linalg.norm(nodes_array[idx] - current_pos)
            if dist < best_dist:
                best_dist = dist
                best_next = idx

        tour.append(best_next)
        unvisited.remove(best_next)
        current = best_next

    return tour
# EVOLVE_END


def calculate_tour_length(nodes, tour):
    """Calculate the total length of a TSP tour.

    Args:
        nodes: List of (x, y) coordinate tuples
        tour: List of node indices representing the tour

    Returns:
        float: Total tour length (including return to start)
    """
    if len(tour) < 2:
        return 0.0

    total = 0.0
    nodes = np.array(nodes)

    for i in range(len(tour) - 1):
        total += np.linalg.norm(nodes[tour[i]] - nodes[tour[i + 1]])

    total += np.linalg.norm(nodes[tour[-1]] - nodes[tour[0]])

    return total


def solve(nodes):
    """Main TSP solving function that delegates to the evolved algorithm.

    Args:
        nodes: List of (x, y) coordinate tuples representing cities

    Returns:
        dict: Solution containing tour and tour length
    """
    tour = nearest_neighbor_tsp(nodes)
    tour_length = calculate_tour_length(nodes, tour)

    return {
        "tour": tour,
        "tour_length": tour_length,
    }


def main():
    """Main entry point for the TSP solver."""
    if len(sys.argv) < 2:
        print("Usage: python solve.py '<input_json>'")
        sys.exit(1)

    input_json = sys.argv[1]
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input")
        sys.exit(1)

    nodes = input_data.get("nodes", [])
    if not nodes:
        print("Error: No nodes provided")
        sys.exit(1)

    result = solve(nodes)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
