"""Generate diverse TSP instances for DyCA multi-distribution evolution.

Creates three categories of instances with distinct characteristics,
allowing DyCA to discover that different instance types benefit from
different algorithmic strategies:

- Small random: 10-20 cities, uniform random — favor exact/exhaustive methods
- Clustered: 30-50 cities in spatial clusters — favor cluster-first-route-second
- Large random: 60-100 cities, uniform random — favor constructive + local search
"""

import json
from pathlib import Path

import numpy as np


def generate_random_instance(n_cities: int, seed: int) -> list:
    """Generate a random uniform TSP instance.

    Args:
        n_cities: Number of cities.
        seed: Random seed.

    Returns:
        List of (x, y) coordinate tuples.
    """
    rng = np.random.RandomState(seed)
    coords = rng.uniform(0, 100, size=(n_cities, 2))
    return [tuple(float(c) for c in coord) for coord in coords]


def generate_clustered_instance(
    n_cities: int, n_clusters: int, seed: int
) -> list:
    """Generate a clustered TSP instance.

    Cities are grouped around cluster centers with Gaussian spread,
    creating structure that cluster-aware algorithms can exploit.

    Args:
        n_cities: Total number of cities.
        n_clusters: Number of spatial clusters.
        seed: Random seed.

    Returns:
        List of (x, y) coordinate tuples.
    """
    rng = np.random.RandomState(seed)

    # Generate cluster centers
    centers = rng.uniform(15, 85, size=(n_clusters, 2))

    # Assign cities to clusters
    per_cluster = n_cities // n_clusters
    remainder = n_cities % n_clusters

    coords = []
    for i in range(n_clusters):
        n = per_cluster + (1 if i < remainder else 0)
        spread = rng.uniform(3, 10)  # Variable cluster tightness
        cluster_pts = centers[i] + rng.normal(0, spread, size=(n, 2))
        # Clamp to [0, 100]
        cluster_pts = np.clip(cluster_pts, 0, 100)
        coords.append(cluster_pts)

    all_coords = np.vstack(coords)
    rng.shuffle(all_coords)
    return [tuple(float(c) for c in coord) for coord in all_coords]


def save_instance(filepath: Path, nodes: list, metadata: dict) -> None:
    """Save a TSP instance to JSON.

    Args:
        filepath: Output file path.
        nodes: List of (x, y) coordinate tuples.
        metadata: Extra metadata to include.
    """
    data = {"nodes": nodes, **metadata}
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> None:
    """Generate all diverse TSP instances."""
    data_dir = Path(__file__).parent / "data" / "diverse"
    data_dir.mkdir(parents=True, exist_ok=True)

    instances = []

    # Category 1: Small random (10-20 cities)
    small_sizes = [10, 12, 15, 15, 18, 20]
    for i, n in enumerate(small_sizes):
        name = f"small_random_{i + 1:02d}.json"
        seed = 42000 + i
        nodes = generate_random_instance(n, seed)
        meta = {"category": "small_random", "n_cities": n}
        instances.append((name, nodes, meta))

    # Category 2: Clustered (30-50 cities, 3-5 clusters)
    clustered_specs = [
        (30, 3), (35, 4), (40, 3), (40, 5), (45, 4), (50, 5),
    ]
    for i, (n, nc) in enumerate(clustered_specs):
        name = f"clustered_{i + 1:02d}.json"
        seed = 43000 + i
        nodes = generate_clustered_instance(n, nc, seed)
        meta = {"category": "clustered", "n_cities": n, "n_clusters": nc}
        instances.append((name, nodes, meta))

    # Category 3: Large random (60-100 cities)
    large_sizes = [60, 70, 75, 80, 90, 100]
    for i, n in enumerate(large_sizes):
        name = f"large_random_{i + 1:02d}.json"
        seed = 44000 + i
        nodes = generate_random_instance(n, seed)
        meta = {"category": "large_random", "n_cities": n}
        instances.append((name, nodes, meta))

    # Save all
    for name, nodes, meta in instances:
        filepath = data_dir / name
        save_instance(filepath, nodes, meta)
        print(f"Generated {filepath.name}: {meta}")

    print(f"\nTotal: {len(instances)} instances in {data_dir}")


if __name__ == "__main__":
    main()
