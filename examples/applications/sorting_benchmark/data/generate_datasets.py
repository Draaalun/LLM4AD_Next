#!/usr/bin/env python3
"""Generate random integer datasets for sorting benchmark."""

import random
from pathlib import Path


def generate_dataset(size: int, output_path: Path) -> None:
    """Generate a dataset with random integers.

    Args:
        size: Number of integers to generate.
        output_path: Path to output file.
    """
    with open(output_path, "w", encoding='UTF-8') as f:
        for _ in range(size):
            # Random integers between -1e6 and 1e6
            num = random.randint(-1_000_000, 1_000_000)
            f.write(f"{num}\n")


def main() -> None:
    """Generate datasets of different sizes."""
    random.seed(42)  # For reproducibility

    # Sizes to generate
    sizes = [1000, 10000]

    # Create output directory
    data_dir = Path(__file__).parent
    small_dir = data_dir / "small"
    small_dir.mkdir(exist_ok=True)

    for size in sizes:
        output_path = small_dir / f"{size}.txt"
        print(f"Generating {size} integers -> {output_path}")
        generate_dataset(size, output_path)

    print("Done!")


if __name__ == "__main__":
    main()
