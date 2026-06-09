#!/usr/bin/env python3
"""Generate sample data instances for the 2D function optimization task.

Each instance contains a pre-computed grid of function values that the
algorithm uses to search for the minimum. Pre-computing avoids needing
the algorithm to evaluate the function itself (keeps the template simple).

Usage:
    python generate_data.py
"""

import json
from pathlib import Path

import numpy as np


def rastrigin_2d(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Rastrigin function in 2D — a common optimization benchmark.

    Global minimum is 0.0 at (0, 0). Has many local minima arranged
    in a regular grid pattern, making it a challenging test for
    optimization algorithms.

    Args:
        x: x-coordinates (scalar or array).
        y: y-coordinates (scalar or array).

    Returns:
        Function values at the given coordinates.
    """
    return 20 + (x**2 - 10 * np.cos(2 * np.pi * x)) + (y**2 - 10 * np.cos(2 * np.pi * y))


def generate_instance(
    function_name: str,
    func,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    grid_size: int,
    true_optimum: list[float],
    true_minimum: float,
    difficulty: str = "easy",
) -> dict:
    """Generate a single function optimization instance.

    Args:
        function_name: Human-readable function name.
        func: Callable(x, y) -> values.
        x_range: (x_min, x_max) domain bounds.
        y_range: (y_min, y_max) domain bounds.
        grid_size: Number of points along each axis.
        true_optimum: Known optimal point [x*, y*].
        true_minimum: Known optimal value f(x*, y*).
        difficulty: Difficulty label for metadata.

    Returns:
        Instance dict ready for JSON serialization.
    """
    xs = np.linspace(x_range[0], x_range[1], grid_size)
    ys = np.linspace(y_range[0], y_range[1], grid_size)
    xx, yy = np.meshgrid(xs, ys)
    zz = func(xx, yy)

    return {
        "description": f"{function_name} on [{x_range[0]}, {x_range[1]}] x [{y_range[0]}, {y_range[1]}]",
        "grid": zz.tolist(),
        "x_range": list(x_range),
        "y_range": list(y_range),
        "grid_size": [grid_size, grid_size],
        "true_optimum": true_optimum,
        "true_minimum": true_minimum,
        "metadata": {
            "function_name": function_name,
            "difficulty": difficulty,
        },
    }


def main():
    """Generate sample instances and save to data/sample/."""
    output_dir = Path(__file__).parent / "data" / "sample"
    output_dir.mkdir(parents=True, exist_ok=True)

    instances = [
        generate_instance(
            function_name="rastrigin_2d",
            func=rastrigin_2d,
            x_range=(-5.0, 5.0),
            y_range=(-5.0, 5.0),
            grid_size=50,
            true_optimum=[0.0, 0.0],
            true_minimum=0.0,
            difficulty="easy",
        ),
    ]

    for i, instance in enumerate(instances, start=1):
        path = output_dir / f"instance_{i:03d}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(instance, f, indent=2)
        print(f"Generated: {path} ({len(json.dumps(instance))} bytes)")


if __name__ == "__main__":
    main()
