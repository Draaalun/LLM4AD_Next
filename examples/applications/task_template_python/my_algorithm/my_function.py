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

EVALUATION PATTERNS:
    Pattern A (Subprocess - like TSP/Sorting):
        - This file is executed as a subprocess: `python my_function.py '<input_json>'`
        - The main() function reads JSON from argv, calls the algorithm, prints JSON result
        - The evaluator parses stdout JSON

    Pattern B (Direct Import - like LunarLander):
        - The evaluator imports this module directly via importlib
        - The evaluator calls the evolvable function directly (no subprocess)
        - The main() function is only used for standalone testing

This template shows Pattern A (subprocess). For Pattern B, the main() function
is optional (only for manual testing) and the evaluator calls the function directly.
"""

import json
import sys

# ===== EVOLVABLE SECTION =====
# The LLM will modify the code between these markers.
# Put all imports needed by the evolvable function inside the markers.

# EVOLVE_START
def my_algorithm(data):
    """Baseline implementation to be evolved by LLM4AD.

    TEMPLATE: Replace this with your baseline algorithm.

    Args:
        data: Input data (format depends on your task).
            E.g. TSP: list of (x, y) tuples; Sorting: list of ints;
            LunarLander: state vector (list of floats).

    Returns:
        Result in the format expected by your evaluator.
            E.g. TSP: list of node indices (tour);
            Sorting: tuple of (comparisons, swaps);
            LunarLander: int action (0-3).
    """
    # Baseline: identity / trivial solution
    return data
# EVOLVE_END
# =============================


def process(data):
    """Fixed wrapper that calls the evolvable function and formats the result.

    TEMPLATE: Adapt this to your task's output format.
    This function is NOT evolved - it provides a stable interface.
    """
    result = my_algorithm(data)
    return {
        "result": result,
        # Add any metrics your evaluator expects in the output JSON:
        # "score": ...,
        # "metric_name": ...,
    }


def main():
    """Entry point for subprocess execution (Pattern A).

    The evaluator runs: python my_function.py '<input_json>'
    and parses the JSON output from stdout.

    For Pattern B (direct import), this function is only used
    for standalone testing / debugging.
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
