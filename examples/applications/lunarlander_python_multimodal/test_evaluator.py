"""Test script to verify the LunarLanderPolicyEvaluatorMultimodal works correctly.

Tests all three behavior storage modes (``"rendered"``, ``"raw"``,
``"none"``), ensuring that visualization data is correctly generated
and that the deferred renderer can reconstruct images from raw data.

Run: uv run python test_evaluator.py
"""

import asyncio
import base64
from pathlib import Path

from lunarlander_evaluator import LunarLanderPolicyEvaluatorMultimodal

from llm4ad.config.schema import EvalContext
from llm4ad.evaluator.renderer import render_visualization


async def test_rendered_mode():
    """Test the evaluator with behavior_storage='rendered'.

    Validates that the evaluator produces pre-rendered base64 PNG images
    alongside the standard metrics and score.
    """
    print("=" * 60)
    print("Test 1: Rendered mode (pre-rendered PNG images)")
    print("=" * 60)

    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "train" / "instance_001.json"
    project_root = current_dir

    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False

    evaluator = LunarLanderPolicyEvaluatorMultimodal()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(project_root),
        timeout=120.0,
        behavior_storage="rendered",
    )

    result = await evaluator.evaluate(cfg)

    # Print standard results
    print(f"\n  Success: {result.success}")
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

    # Validate expected metrics
    expected_metrics = ["episode_reward", "fuel_consumed", "success", "execution_time_ms"]
    has_all_metrics = all(m in result.metrics for m in expected_metrics)

    # Validate behavior data (multimodal-specific)
    has_behavior = False
    if result.behavior is not None:
        has_behavior = True
        print("\n  Behavior Data:")
        print(f"    Observation: {result.behavior.observation[:100]}...")
        print(f"    Num visualizations: {len(result.behavior.visualizations)}")

        for i, viz in enumerate(result.behavior.visualizations):
            print(f"    Visualization {i}: label='{viz.label}', type='{viz.media_type}'")
            if viz.data_base64:
                img_bytes = base64.b64decode(viz.data_base64)
                print(f"      Image size: {len(img_bytes) / 1024:.1f} KB")

                # Save test output for visual inspection
                output_path = current_dir / "test_output_rendered.png"
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                print(f"      Saved to: {output_path}")
            else:
                print("      [!] No pre-rendered image (unexpected in rendered mode)")
    else:
        print("\n  [!] No behavior data returned")

    passed = result.success and has_all_metrics and has_behavior
    if passed:
        print("\n[PASS] Rendered mode test PASSED!")
    else:
        print("\n[FAIL] Rendered mode test FAILED!")
        if not result.success:
            print(f"  Reason: evaluation failed - {result.error_message}")
        if not has_all_metrics:
            missing = [m for m in expected_metrics if m not in result.metrics]
            print(f"  Reason: missing metrics: {missing}")
        if not has_behavior:
            print("  Reason: no behavior data returned")

    return passed


async def test_raw_mode():
    """Test the evaluator with behavior_storage='raw' and deferred rendering.

    Validates that the evaluator stores compact raw data and that the
    registered renderer can reconstruct the image on demand.
    """
    print("\n" + "=" * 60)
    print("Test 2: Raw mode (deferred rendering)")
    print("=" * 60)

    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "train" / "instance_001.json"
    project_root = current_dir

    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False

    evaluator = LunarLanderPolicyEvaluatorMultimodal()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(project_root),
        timeout=120.0,
        behavior_storage="raw",
    )

    result = await evaluator.evaluate(cfg)

    print(f"\n  Success: {result.success}")
    print(f"  Score: {result.score:.4f}")

    if not result.success:
        print(f"  Error: {result.error_message}")
        print("\n[FAIL] Raw mode test FAILED!")
        return False

    if result.behavior is None:
        print("  [!] No behavior data returned")
        print("\n[FAIL] Raw mode test FAILED!")
        return False

    print(f"  Observation: {result.behavior.observation[:100]}...")
    print(f"  Num visualizations: {len(result.behavior.visualizations)}")

    passed = True
    for i, viz in enumerate(result.behavior.visualizations):
        print(f"\n  Visualization {i}:")
        print(f"    Label: {viz.label}")
        print(f"    Has raw_data: {viz.raw_data is not None}")
        print(f"    Renderer: {viz.renderer}")

        if viz.raw_data is None or viz.renderer is None:
            print("    [!] Missing raw_data or renderer name")
            passed = False
            continue

        # Test deferred rendering via the registry
        print("    Testing deferred rendering...")
        rendered_b64 = render_visualization(viz)

        if rendered_b64:
            img_bytes = base64.b64decode(rendered_b64)
            print(f"    Rendered image size: {len(img_bytes) / 1024:.1f} KB")

            output_path = current_dir / "test_output_raw.png"
            with open(output_path, "wb") as f:
                f.write(img_bytes)
            print(f"    Saved to: {output_path}")
        else:
            print("    [!] Deferred rendering failed")
            passed = False

    if passed:
        print("\n[PASS] Raw mode test PASSED!")
    else:
        print("\n[FAIL] Raw mode test FAILED!")

    return passed


async def test_none_mode():
    """Test the evaluator with behavior_storage='none'.

    Validates that the evaluator returns correct metrics and score
    without generating any behavior data.
    """
    print("\n" + "=" * 60)
    print("Test 3: None mode (no behavior data)")
    print("=" * 60)

    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "train" / "instance_001.json"
    project_root = current_dir

    if not data_path.exists():
        print(f"[X] Data file not found: {data_path}")
        return False

    evaluator = LunarLanderPolicyEvaluatorMultimodal()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(project_root),
        timeout=120.0,
        behavior_storage="none",
    )

    result = await evaluator.evaluate(cfg)

    print(f"\n  Success: {result.success}")
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

    # Validate metrics
    expected_metrics = ["episode_reward", "fuel_consumed", "success", "execution_time_ms"]
    has_all_metrics = all(m in result.metrics for m in expected_metrics)

    # In "none" mode, behavior should be None
    no_behavior = result.behavior is None
    if no_behavior:
        print("\n  Behavior data: None (expected for none mode)")
    else:
        print("\n  [!] Behavior data was returned (unexpected in none mode)")

    passed = result.success and has_all_metrics and no_behavior
    if passed:
        print("\n[PASS] None mode test PASSED!")
    else:
        print("\n[FAIL] None mode test FAILED!")
        if not result.success:
            print(f"  Reason: evaluation failed - {result.error_message}")
        if not has_all_metrics:
            missing = [m for m in expected_metrics if m not in result.metrics]
            print(f"  Reason: missing metrics: {missing}")
        if not no_behavior:
            print("  Reason: behavior data was returned in none mode")

    return passed


if __name__ == "__main__":
    success_rendered = asyncio.run(test_rendered_mode())
    success_raw = asyncio.run(test_raw_mode())
    success_none = asyncio.run(test_none_mode())

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Rendered mode: {'PASS' if success_rendered else 'FAIL'}")
    print(f"  Raw mode:      {'PASS' if success_raw else 'FAIL'}")
    print(f"  None mode:     {'PASS' if success_none else 'FAIL'}")
    print("=" * 60)

    exit(0 if (success_rendered and success_raw and success_none) else 1)
