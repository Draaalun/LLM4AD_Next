"""Test script template for verifying evaluator correctness.

TEMPLATE INSTRUCTIONS:
    1. Adapt the EvalContext to match your task
    2. Update the metric validation to check your expected metrics
    3. Run: uv run python test_evaluator.py

This script tests the evaluator independently of the full LLM4AD pipeline,
making it easy to debug evaluator issues in isolation.
"""

import asyncio
from pathlib import Path

# TEMPLATE: Change import to your evaluator class
from my_evaluator import MyTaskEvaluator

from llm4ad.config.schema import EvalContext


async def test_evaluator():
    """Test the evaluator with the default algorithm implementation."""
    print("Testing MyTaskEvaluator with default algorithm...")

    # Get directory paths
    current_dir = Path(__file__).parent

    # TEMPLATE: Set data_path to one of your data files
    data_path = current_dir / "data" / "sample" / "instance_001.json"

    # project_root: the directory containing the algorithm code
    # In local testing, this is the task directory (algorithm lives in subdir)
    project_root = current_dir

    # Verify files exist
    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False

    # Create evaluator and config
    evaluator = MyTaskEvaluator()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(project_root),
        timeout=60.0,
    )

    # Run evaluation
    result = await evaluator.evaluate(cfg)

    # Print results
    print("\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Score: {result.score:.4f}")
    print(f"  Duration: {result.duration_ms:.2f}ms")

    if result.metrics:
        print("  Metrics:")
        for name, value in result.metrics.items():
            if isinstance(value, float):
                print(f"    {name}: {value:.4f}")
            else:
                print(f"    {name}: {value}")

    if result.error_message:
        print(f"  Error: {result.error_message}")

    if result.metadata:
        print("  Metadata:")
        for key, value in result.metadata.items():
            print(f"    {key}: {value}")

    # TEMPLATE: Validate expected metrics are present
    expected_metrics = ["primary_score", "execution_time_ms"]
    has_all_metrics = all(m in result.metrics for m in expected_metrics)

    if result.success and has_all_metrics:
        print("\n[PASS] Test PASSED! The evaluator is working correctly.")
        return True
    else:
        print("\n[FAIL] Test FAILED!")
        if not result.success:
            print(f"  Reason: {result.error_message}")
        elif not has_all_metrics:
            missing = [m for m in expected_metrics if m not in result.metrics]
            print(f"  Reason: Missing metrics: {missing}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_evaluator())
    exit(0 if success else 1)
