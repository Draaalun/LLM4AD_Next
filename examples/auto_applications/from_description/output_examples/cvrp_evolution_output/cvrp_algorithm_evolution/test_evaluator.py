#!/usr/bin/env python3
"""End-to-end test for the CVRP multimodal evaluator.

Imports the evaluator class, creates an EvalContext pointing to the
sample data instance, runs evaluate(), and checks that the result
contains expected metrics and behavior data.
"""

import asyncio
import sys
from pathlib import Path

# Ensure the project root is on the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cvrp_algorithm_evolution_evaluator import CVRPAlgorithmEvolutionEvaluatorMultimodal
from llm4ad.config.schema import EvalContext


async def test_evaluator():
    data_path = Path(__file__).parent / "data" / "sample" / "instance_001.json"

    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(Path(__file__).parent),
        timeout=120.0,
        behavior_storage="rendered",
    )

    evaluator = CVRPAlgorithmEvolutionEvaluatorMultimodal()
    result = await evaluator.evaluate(cfg)

    expected_metrics = ["total_distance", "num_routes", "feasibility_penalty"]

    if not result.success:
        print(f"[FAIL] Evaluator returned success=False: {result}")
        sys.exit(1)

    missing = [m for m in expected_metrics if m not in result.metrics]
    if missing:
        print(f"[FAIL] Missing metrics: {missing}")
        sys.exit(1)

    print(f"[PASS] Metrics: {result.metrics}")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(test_evaluator())