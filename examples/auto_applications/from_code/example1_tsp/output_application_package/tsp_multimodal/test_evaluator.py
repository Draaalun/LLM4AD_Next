#!/usr/bin/env python3
"""End-to-end test for the TSP multimodal evaluator.

Imports the evaluator class, creates an EvalContext pointing to the
sample data instance, calls evaluate(), and checks success and metrics.
"""

import asyncio
import json
import sys
from pathlib import Path


def main():
    # Determine paths
    project_root = Path(__file__).resolve().parent
    data_path = project_root / "data" / "sample" / "instance_001.json"

    if not data_path.exists():
        print(f"[FAIL] Sample data not found at {data_path}")
        sys.exit(1)

    # Check algorithm file exists
    algo_file = project_root / "algorithm" / "solve.py"
    if not algo_file.exists():
        algo_file = project_root / "solve.py"
    if not algo_file.exists():
        print(f"[FAIL] solve.py not found in {project_root}")
        sys.exit(1)

    # Import evaluator
    sys.path.insert(0, str(project_root))
    from tsp_multimodal_evaluator import TSPMultimodalEvaluator

    evaluator = TSPMultimodalEvaluator()

    # Verify evaluator properties
    assert evaluator.name == "tsp_multimodal_evaluator", (
        f"Wrong name: {evaluator.name}"
    )
    assert len(evaluator.metrics) >= 1, "No metrics defined"
    assert evaluator.metrics[0].name == "tour_length", (
        f"Wrong metric name: {evaluator.metrics[0].name}"
    )

    # Test each behavior_storage mode
    modes_to_test = ["none", "raw", "rendered"]
    all_passed = True

    for mode in modes_to_test:
        print(f"\n--- Testing behavior_storage='{mode}' ---")

        cfg = type("EvalContext", (), {
            "project_root": str(project_root),
            "data_path": str(data_path),
            "timeout": 60,
            "behavior_storage": mode,
        })()

        result = asyncio.run(evaluator.evaluate(cfg))

        if not result.success:
            print(f"[FAIL] mode={mode}: {result.error_message}")
            all_passed = False
            continue

        # Check score is negative (minimization)
        if result.score >= 0:
            print(
                f"[FAIL] mode={mode}: Score should be negative "
                f"(got {result.score})"
            )
            all_passed = False
            continue

        # Check tour_length metric exists and is positive
        tl = result.metrics.get("tour_length")
        if tl is None or tl <= 0:
            print(
                f"[FAIL] mode={mode}: Invalid tour_length metric: {tl}"
            )
            all_passed = False
            continue

        # Check score == -tour_length
        if abs(result.score + tl) > 1e-6:
            print(
                f"[FAIL] mode={mode}: score ({result.score}) != "
                f"-tour_length ({-tl})"
            )
            all_passed = False
            continue

        print(f"  Score: {result.score:.2f}")
        print(f"  Tour length: {tl:.2f}")
        print(f"  Duration: {result.duration_ms:.1f}ms")

        # Check behavior data for non-none modes
        if mode == "none":
            print(f"  Behavior: None (expected)")
        elif result.behavior is not None:
            print(f"  Observation: {result.behavior.observation[:80]}...")
            if result.behavior.visualizations:
                viz = result.behavior.visualizations[0]
                print(f"  Visualization label: {viz.label}")
                if mode == "rendered" and viz.data_base64:
                    print(
                        f"  Image size: "
                        f"{len(viz.data_base64)} chars (base64)"
                    )
                elif mode == "raw" and viz.raw_data:
                    print(f"  Raw data keys: {list(viz.raw_data.keys())}")
            else:
                print("  [WARN] No visualizations in behavior data")
        else:
            print(f"  [WARN] No behavior data for mode={mode}")