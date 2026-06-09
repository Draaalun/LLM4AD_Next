"""Generate TSP test instances in JSON format.

This script creates random TSP instances for testing the TSP solver.
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

    # Generate random coordinates in [0, 100] range
    coordinates = np.random.uniform(0, 100, size=(n_cities, 2))

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
    """Generate all test instances."""
    data_dir = Path(__file__).parent / "data" / "small"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Generate instances of different sizes
    instances = [
        ("instance_001.json", 10, 20240101),
        ("instance_002.json", 15, 20240102),
        ("instance_003.json", 20, 20240103),
        ("instance_004.json", 25, 20240104),
        ("instance_005.json", 30, 20240105),
    ]

    for filename, n_cities, seed in instances:
        nodes = generate_tsp_instance(n_cities, seed)
        filepath = data_dir / filename
        save_instance(str(filepath), nodes)
        print(f"Generated {filepath} with {n_cities} cities")


if __name__ == "__main__":
    main()
