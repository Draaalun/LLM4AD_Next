#!/usr/bin/env python3
"""Algorithm file template with EVOLVE markers for LLM4AD optimization.

TEMPLATE INSTRUCTIONS:
    1. Rename this file to match your task (e.g. solve.py, choose_action.py)
    2. Replace the evolvable function with your baseline algorithm
    3. Keep the EVOLVE_START / EVOLVE_END markers around the evolvable region
    4. Keep the fixed scaffolding (main, IO) outside the markers

IMPORTANT CONVENTIONS:
    - The code between EVOLVE_START and EVOLVE_END is what the LLM will modify
    - Everything outside these markers is FIXED and will not be evolved
    - The evolvable function should be self-contained (no external state)
    - Imports used by the evolvable function should be inside the markers

This template demonstrates a 2D function optimization task:
    Input:  Pre-computed grid of function values + domain bounds
    Output: Search trajectory + best point found
"""

import json
import random
import sys

# ===== EVOLVABLE SECTION =====
# The LLM will modify the code between these markers.
# Put all imports needed by the evolvable function inside the markers.

# EVOLVE_START


def my_algorithm(data):
    """Find the minimum of a 2D function sampled on a grid.

    TODO: Replace this baseline with your algorithm implementation.

    Args:
        data: Dict with keys:
            - "grid": 2D list of f(x,y) values (grid[row][col])
            - "x_range": [x_min, x_max]
            - "y_range": [y_min, y_max]
            - "grid_size": [n_rows, n_cols]

    Returns:
        Dict with keys:
            - "trajectory": List of [x, y, f_value] evaluated points
            - "best_point": [x, y] of the proposed minimum
            - "best_value": f(x, y) at the proposed minimum
    """
    grid = data["grid"]
    x_min, x_max = data["x_range"]
    y_min, y_max = data["y_range"]
    n_rows, n_cols = data["grid_size"]

    trajectory = []
    best_point = None
    best_value = float("inf")

    # Baseline: random search with 50 samples
    random.seed(42)
    for _ in range(50):
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)

        # Look up function value from grid (nearest grid point)
        col = int((x - x_min) / (x_max - x_min) * (n_cols - 1))
        row = int((y - y_min) / (y_max - y_min) * (n_rows - 1))
        col = max(0, min(col, n_cols - 1))
        row = max(0, min(row, n_rows - 1))
        f_value = grid[row][col]

        trajectory.append([x, y, f_value])

        if f_value < best_value:
            best_value = f_value
            best_point = [x, y]

    return {
        "trajectory": trajectory,
        "best_point": best_point,
        "best_value": best_value,
    }
# EVOLVE_END
# =============================


def process(data):
    """Fixed wrapper that calls the evolvable function and formats the result.

    TODO: Adapt this to your task's output format.
    This function is NOT evolved - it provides a stable interface.
    """
    result = my_algorithm(data)
    return {
        "trajectory": result["trajectory"],
        "best_point": result["best_point"],
        "best_value": result["best_value"],
    }


def main():
    """Entry point for subprocess execution (Pattern A).

    The evaluator runs: python my_function.py '<input_json>'
    and parses the JSON output from stdout.
    """
    if len(sys.argv) < 2:
        print("Usage: python my_function.py '<input_json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"Error parsing input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    result = process(input_data)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
