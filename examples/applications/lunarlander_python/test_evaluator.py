"""Test script to verify the LunarLanderPolicyEvaluator works correctly."""

import asyncio
from pathlib import Path

from lunarlander_evaluator import LunarLanderPolicyEvaluator

from llm4ad.config.schema import EvalContext


async def test_evaluator():
    """Test the LunarLanderPolicyEvaluator with the default policy implementation."""
    print("Testing LunarLanderPolicyEvaluator with default policy...")

    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "train" / "instance_001.json"
    project_root = current_dir

    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False

    evaluator = LunarLanderPolicyEvaluator()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(project_root),
        timeout=120.0,
    )

    result = await evaluator.evaluate(cfg)

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

    expected_metrics = ["episode_reward", "fuel_consumed", "success", "execution_time_ms"]
    has_all_metrics = all(m in result.metrics for m in expected_metrics)

    if result.success and has_all_metrics:
        print("\n[PASS] Test PASSED! The evaluator is working correctly.")
        print(f"  Episode reward: {result.metrics.get('episode_reward', 0):.2f}")
        print(f"  Fuel consumed: {result.metrics.get('fuel_consumed', 0):.2f}")
        print(f"  Success: {result.metrics.get('success', 0):.0%}")
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
