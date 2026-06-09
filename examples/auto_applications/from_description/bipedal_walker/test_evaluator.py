#!/usr/bin/env python3
"""Test script for the bipedal_walker evaluator.

Exercises the evaluator end-to-end with a sample data file.
"""

import asyncio
from pathlib import Path
from bipedal_walker_evaluator import BipedalWalkerEvaluator
from llm4ad.config.schema import EvalContext


async def test_evaluator():
    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "sample" / "instance_001.json"
    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False

    evaluator = BipedalWalkerEvaluator()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(current_dir),
        timeout=120.0,
    )
    result = await evaluator.evaluate(cfg)
    print(f"Success: {result.success}")
    print(f"Score: {result.score}")
    print(f"Metrics: {result.metrics}")
    if result.error_message:
        print(f"Error: {result.error_message}")

    expected_metrics = ["mean_score"]
    has_all = all(m in result.metrics for m in expected_metrics)

    if result.success and has_all:
        print("[PASS] Test PASSED")
        return True
    else:
        print("[FAIL] Test FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_evaluator())
    exit(0 if success else 1)