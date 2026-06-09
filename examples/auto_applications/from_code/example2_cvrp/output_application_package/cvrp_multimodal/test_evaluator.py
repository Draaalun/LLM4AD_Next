"""End-to-end test for the CVRP multimodal evaluator.

Creates an EvalContext pointing to the sample data instance, runs
evaluate(), and checks that the result is successful with expected metrics.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


async def test_evaluator():
    project_root = Path(__file__).resolve().parent
    data_path = project_root / "data" / "sample" / "instance_001.json"

    if not data_path.exists():
        print(f"[FAIL] Sample data not found at {data_path}")
        return False

    # Verify algorithm file exists
    algo_file = project_root / "algorithm" / "evaluation.py"
    if not algo_file.exists():
        algo_file = project_root / "evaluation.py"
        if not algo_file.exists():
            print(f"[FAIL] evaluation.py not found")
            return False

    # Import evaluator
    sys.path.insert(0, str(project_root))
    from cvrp_multimodal_evaluator import CVRPMultimodalEvaluator

    evaluator = CVRPMultimodalEvaluator()

    # Verify metrics
    assert evaluator.name == "cvrp_multimodal_evaluator", (
        f"Expected name 'cvrp_multimodal_evaluator', got '{evaluator.name}'"
    )
    assert len(evaluator.metrics) == 1, (
        f"Expected 1 metric, got {len(evaluator.metrics)}"
    )
    assert evaluator.metrics[0].name == "normalized_gap"

    # Build EvalContext
    from llm4ad.config.schema import EvalContext

    cfg = EvalContext(
        project_root=str(project_root),
        data_path=str(data_path),
        timeout=120.0,
        behavior_storage="rendered",
    )

    # Run evaluation
    result = await evaluator.evaluate(cfg)

    # Check results
    all_pass = True

    if not result.success:
        print(f"[FAIL] Evaluation failed: {result.error_message}")
        return False
    else:
        print(f"[PASS] Evaluation succeeded")

    if "normalized_gap" not in result.metrics:
        print(f"[FAIL] Missing 'normalized_gap' metric")
        all_pass = False
    else:
        ng = result.metrics["normalized_gap"]
        print(f"[PASS] normalized_gap = {ng:.4f}")
        if ng > 0:
            print(f"  (Beat the baseline!)")
        elif ng == 0:
            print(f"  (Matched the baseline)")
        else:
            print(f"  (Gap of {-ng*100:.2f}% to baseline)")

    if result.score is None:
        print(f"[FAIL] Score is None")
        all_pass = False
    else:
        print(f"[PASS] Score = {result.score:.4f}")

    if result.duration_ms is not None and result.duration_ms > 0:
        print(f"[PASS] Duration = {result.duration_ms:.1f}ms")
    else:
        print(f"[FAIL] Invalid duration: {result.duration_ms}")
        all_pass = False

    # Check behavior data
    if result.behavior is not None:
        print(f"[PASS] BehaviorData present")
        if result.behavior.observation:
            print(f"  Observation: {result.behavior.observation[:120]}...")
        if result.behavior.visualizations:
            viz = result.behavior.visualizations[0]
            print(f"  Visualization label: {viz.label}")
            if viz.data_base64:
                img_size = len(viz.data_base64)
                print(f"  Image size: {img_size} chars (base64)")
                print(f"[PASS] Rendered image present")
            else:
                print(f"[FAIL] No rendered image in 'rendered' mode")
                all_pass = False
        else:
            print(f"[FAIL] No visualizations in BehaviorData")
            all_pass = False
    else:
        print(f"[FAIL] No BehaviorData returned")
        all_pass = False

    # Test 'raw' mode
    cfg_raw = EvalContext(
        project_root=str(project_root),
        data_path=str(data_path),
        timeout=120.0,
        behavior_storage="raw",
    )
    result_raw = await evaluator.evaluate(cfg_raw)
    if result_raw.success and result_raw.behavior:
        viz_raw = result_raw.behavior.visualizations[0]
        if viz_raw.raw_data and viz_raw.renderer == "cvrp_solution":
            print(f"[PASS] Raw mode: raw_data present, renderer='cvrp_solution'")
        else:
            print(f"[FAIL] Raw mode: missing raw_data or renderer")
            all_pass = False
    else:
        print(f"[FAIL] Raw mode evaluation failed")
        all_pass = False

    # Test 'none' mode
    cfg_none = EvalContext(
        project_root=str(project_root),
        data_path=str(data_path),
        timeout=120.0,
        behavior_storage="none",
    )
    result_none = await evaluator.evaluate(cfg_none)
    if result_none.success and result_none.behavior is None:
        print(f"[PASS] None mode: no BehaviorData (correct)")
    elif result_none.success:
        print(f"[FAIL] None mode: BehaviorData should be None")
        all_pass = False
    else:
        print(f"[FAIL] None mode evaluation failed")
        all_pass = False

    print()
    if all_pass:
        print("[PASS] All tests passed")
    else:
        print("[FAIL] Some tests failed")

    return all_pass


if __name__ == "__main__":
    success = asyncio.run(test_evaluator())
    sys.exit(0 if success else 1)