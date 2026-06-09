#!/usr/bin/env python3
"""Test script to verify the PythonSortingEvaluator works correctly."""

import asyncio
from pathlib import Path

from llm4ad.config.schema import EvalContext
from sorting_evaluator import PythonSortingEvaluator


async def test_evaluator():
    """Test the PythonSortingEvaluator with the bubble sort implementation."""
    print("Testing PythonSortingEvaluator with bubble sort...")

    # Get the directory paths
    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "small" / "test_001.txt"
    project_root = current_dir / "sorting_algorithm"

    # Verify files exist
    if not data_path.exists():
        print(f"✗ Data file not found: {data_path}")
        return False

    if not project_root.exists():
        print(f"✗ Project root not found: {project_root}")
        return False

    evaluator = PythonSortingEvaluator()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(project_root),
        timeout=60.0,
    )

    result = await evaluator.evaluate(cfg)

    print("\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Score: {result.score}")
    print(f"  Duration: {result.duration_ms:.2f}ms")
    if result.metrics:
        print("  Metrics:")
        for name, value in result.metrics.items():
            print(f"    {name}: {value}")

    if result.error_message:
        print(f"  Error: {result.error_message}")

    # Check if the test passed
    is_correct = result.metrics.get("correct", 0) == 1.0

    if result.success and is_correct:
        print("\n✓ Test PASSED! The evaluator is working correctly.")
        print(f"  Sorted 10 elements in {result.duration_ms:.2f}ms")
        print(f"  Comparisons: {result.metrics.get('comparisons', 'N/A')}")
        print(f"  Swaps: {result.metrics.get('swaps', 'N/A')}")
        return True
    else:
        print(f"\n✗ Test FAILED!")
        if not result.success:
            print(f"  Reason: {result.error_message}")
        elif not is_correct:
            print(f"  Reason: Sorting result is incorrect")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_evaluator())
    exit(0 if success else 1)
