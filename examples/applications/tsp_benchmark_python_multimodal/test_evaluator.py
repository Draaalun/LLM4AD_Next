"""Test script to verify the PythonTSPEvaluatorMultimodal works correctly.

Tests the evaluator in both storage modes:
1. **Rendered mode**: validates metrics + pre-rendered base64 PNG
2. **Raw mode**: validates raw data + deferred rendering via renderer

Both modes should produce identical images — the difference is only
when the rendering happens (at evaluation time vs. on demand).
"""

import asyncio
import base64
from pathlib import Path

from tsp_evaluator import PythonTSPEvaluatorMultimodal

from llm4ad.config.schema import EvalContext


async def _run_test(behavior_storage: str) -> bool:
    """Run the evaluator with a specific behavior_storage mode.

    Args:
        behavior_storage: One of "rendered", "raw", "none".

    Returns:
        True if the test passed, False otherwise.
    """
    print(f"\n{'=' * 60}")
    print(f"  Testing behavior_storage={behavior_storage!r}")
    print(f"{'=' * 60}")

    current_dir = Path(__file__).parent
    data_path = current_dir / "data" / "small" / "instance_001.json"
    project_root = current_dir / "tsp_algorithm"

    if not data_path.exists():
        print(f"  [X] Data file not found: {data_path}")
        return False

    if not (project_root / "solve.py").exists():
        print(f"  [X] solve.py not found in: {project_root}")
        return False

    evaluator = PythonTSPEvaluatorMultimodal()
    cfg = EvalContext(
        data_path=str(data_path),
        project_root=str(project_root),
        timeout=60.0,
        behavior_storage=behavior_storage,
    )

    result = await evaluator.evaluate(cfg)

    # Print result summary
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

    # Check basic success
    expected_metrics = ["tour_length", "valid_tour", "execution_time_ms"]
    has_all_metrics = all(m in result.metrics for m in expected_metrics)

    if not result.success:
        print(f"\n  [FAIL] Evaluation failed: {result.error_message}")
        return False
    if not has_all_metrics:
        missing = [m for m in expected_metrics if m not in result.metrics]
        print(f"\n  [FAIL] Missing metrics: {missing}")
        return False

    # Check behavior data based on mode
    print("\n  Behavior Data:")
    if behavior_storage == "none":
        if result.behavior is not None:
            print("  [FAIL] Expected no behavior for 'none' mode")
            return False
        print("    Has behavior: NO (expected for 'none' mode)")
        print(f"\n  [PASS] {behavior_storage!r} mode test passed!")
        return True

    if result.behavior is None:
        print(f"  [FAIL] Expected behavior data for {behavior_storage!r} mode")
        return False

    print("    Has behavior: YES")
    print(f"    Observation: {result.behavior.observation}")
    print(f"    Visualizations: {len(result.behavior.visualizations)}")

    if not result.behavior.visualizations:
        print(f"  [FAIL] No visualizations for {behavior_storage!r} mode")
        return False

    viz = result.behavior.visualizations[0]

    if behavior_storage == "rendered":
        # Rendered mode: should have data_base64 directly
        if not viz.data_base64:
            print("  [FAIL] No data_base64 in rendered mode")
            return False
        img_size = len(viz.data_base64)
        print(
            f"    - {viz.label}: {img_size} chars base64 "
            f"({img_size * 3 // 4 // 1024} KB approx)"
        )

        # Save for visual inspection
        img_bytes = base64.b64decode(viz.data_base64)
        output_path = current_dir / "test_tour_output_rendered.png"
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print(f"\n    Tour image saved to: {output_path}")

    elif behavior_storage == "raw":
        # Raw mode: should have raw_data + renderer, NOT data_base64
        if viz.data_base64 is not None:
            print("  [FAIL] data_base64 should be None in raw mode")
            return False
        if viz.raw_data is None:
            print("  [FAIL] No raw_data in raw mode")
            return False
        if viz.renderer != "tsp_tour":
            print(f"  [FAIL] Expected renderer='tsp_tour', got {viz.renderer!r}")
            return False

        print(f"    - {viz.label}: raw_data keys={list(viz.raw_data.keys())}")
        print(f"    - renderer: {viz.renderer}")

        # Verify raw_data schema
        for key in ("nodes", "tour", "tour_length", "n_nodes"):
            if key not in viz.raw_data:
                print(f"  [FAIL] Missing key {key!r} in raw_data")
                return False

        # Test deferred rendering via render_visualization
        from llm4ad.evaluator.renderer import render_visualization

        rendered = render_visualization(viz)
        if rendered is None:
            print("  [FAIL] Deferred rendering returned None")
            return False
        print(f"    - Deferred render OK: {len(rendered)} chars base64")

        # Save deferred-rendered image for visual inspection
        img_bytes = base64.b64decode(rendered)
        output_path = current_dir / "test_tour_output_raw.png"
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print(f"\n    Tour image (deferred render) saved to: {output_path}")

    print(f"\n  [PASS] {behavior_storage!r} mode test passed!")
    print(f"    Tour length: {result.metrics.get('tour_length', 0):.2f}")
    print(f"    Valid tour: {result.metrics.get('valid_tour', 0):.0f}")
    print(f"    Execution time: {result.metrics.get('execution_time_ms', 0):.2f}ms")
    return True


async def main():
    """Run all evaluator tests."""
    print("Testing PythonTSPEvaluatorMultimodal...")

    all_passed = True
    for mode in ("rendered", "raw", "none"):
        passed = await _run_test(mode)
        if not passed:
            all_passed = False

    print(f"\n{'=' * 60}")
    if all_passed:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print(f"{'=' * 60}")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
