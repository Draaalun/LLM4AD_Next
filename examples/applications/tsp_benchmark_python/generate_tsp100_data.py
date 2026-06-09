"""Generate TSP100 test instances in JSON format.

This script creates 16 random TSP instances with 100 cities each,
coordinates sampled uniformly from [0, 1].
"""

import json
from pathlib import Path

import numpy as np


def generate_tsp_instance(n_cities: int, seed: int = None) -> list:
    """Generate a random TSP instance.

    Args:
        n_cities: Number of cities (nodes)
        seed: Random seed for reproducibility

    Returns:
        list: List of (x, y) coordinate tuples
    """
    if seed is not None:
        np.random.seed(seed)

    coordinates = np.random.uniform(0, 1, size=(n_cities, 2))

    return [tuple(coord) for coord in coordinates]


def save_instance(filename: str, nodes: list):
    """Save a TSP instance to a JSON file.

    Args:
        filename: Path to output file
        nodes: List of (x, y) coordinate tuples
    """
    data = {"nodes": nodes}

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    """Generate all TSP100 test instances."""
    data_dir = Path(__file__).parent / "data" / "TSP100"
    data_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 17):
        seed = 20260400 + i
        nodes = generate_tsp_instance(100, seed)
        filepath = data_dir / f"instance_{i:03d}.json"
        save_instance(str(filepath), nodes)
        print(f"Generated {filepath} with 100 cities (seed={seed})")


if __name__ == "__main__":
    main()
