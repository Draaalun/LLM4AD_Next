"""View algorithm behavior with silent fallback across all storage modes.

Demonstrates the framework's "silent degradation" rendering chain:
  1. ``data_base64`` exists  -> return directly         (rendered mode)
  2. ``raw_data`` + renderer -> render on demand         (raw mode)
  3. nothing stored          -> re-run evaluator -> image (none mode)

The frontend never needs to know which storage mode was used at evolution
time -- it always gets an image.

Usage:
    python view_algorithm.py                   # interactive: list all, pick one
    python view_algorithm.py <algorithm_id>    # show specific algorithm
    python view_algorithm.py --best            # show the best-scoring algorithm
"""

import base64
import io
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EXAMPLE_DIR = Path(__file__).parent
RUNS_ROOT = EXAMPLE_DIR / "runs"
EVALUATOR_SCRIPT = EXAMPLE_DIR / "my_evaluator.py"
DATASET_DIR = EXAMPLE_DIR / "data" / "sample"
PROJECT_ROOT = EXAMPLE_DIR / "my_algorithm"


# ---------------------------------------------------------------------------
# 1. Locate the run directory
# ---------------------------------------------------------------------------


def _find_latest_run() -> Path:
    """Find the latest run directory (deepest run_id folder)."""
    candidates = sorted(
        RUNS_ROOT.rglob("generated"), key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        print("No runs found under", RUNS_ROOT)
        sys.exit(1)
    return candidates[-1]


# ---------------------------------------------------------------------------
# 2. Index all algorithms in the run
# ---------------------------------------------------------------------------


def _index_algorithms(generated_dir: Path) -> list[dict]:
    """Parse all algorithm JSON files and return summary list."""
    algorithms = []
    for json_path in sorted(generated_dir.glob("*.json")):
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        score = (data.get("evaluation") or {}).get("score")
        n_viz = sum(
            len(bd.get("visualizations", []))
            for bd in data.get("behavior_data", [])
        )
        algorithms.append({
            "json_path": json_path,
            "id": data.get("id", "?"),
            "name": data.get("name", "?"),
            "island_id": data.get("island_id"),
            "generation": data.get("generation"),
            "operator": (data.get("generation_meta") or {}).get("operator", "?"),
            "score": score,
            "n_viz": n_viz,
        })
    return algorithms


# ---------------------------------------------------------------------------
# 3. Display one algorithm (with silent fallback rendering)
# ---------------------------------------------------------------------------


def _display_algorithm(json_path: Path) -> None:
    """Load an algorithm and display its behavior images.

    Applies the silent fallback rendering chain:
    1. Pre-rendered base64  -> use directly
    2. Raw data + renderer  -> deferred render
    3. No behavior data     -> re-run evaluator subprocess
    """
    import importlib.util

    from llm4ad.evaluator.renderer import render_visualization
    from llm4ad.planner.base import Algorithm

    # Import evaluator module to register the "my_task_contour" renderer
    spec = importlib.util.spec_from_file_location(
        "my_evaluator", str(EVALUATOR_SCRIPT),
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    algorithm = Algorithm.load(json_path)

    # Print algorithm summary
    score = algorithm.evaluation.score if algorithm.evaluation else None
    operator = algorithm.generation_meta.operator if algorithm.generation_meta else "?"
    print(f"\n{'=' * 60}")
    print(f"  Algorithm : {algorithm.name}")
    print(f"  ID        : {algorithm.id}")
    print(f"  Island    : {algorithm.island_id}  |  Generation: {algorithm.generation}")
    print(f"  Operator  : {operator}")
    print(f"  Score     : {score}")
    print(f"  Parents   : {algorithm.parent_ids or 'none (initial)'}")
    print(f"{'=' * 60}")
    print(f"\n  Description:\n  {algorithm.description[:200]}...")

    # --- Silent fallback: try cached/deferred rendering first ---
    images = []
    for bd in algorithm.behavior_data:
        for viz in bd.visualizations:
            # Determine source before render_visualization mutates viz
            if viz.data_base64 is not None:
                source = "cached (rendered mode)"
            elif viz.raw_data is not None and viz.renderer is not None:
                source = f"deferred render (raw mode, renderer={viz.renderer})"
            else:
                source = "unavailable"

            # Silent fallback: render_visualization handles both cases
            image_b64 = render_visualization(viz)
            if image_b64:
                images.append({
                    "title": viz.label,
                    "observation": bd.observation,
                    "bytes": base64.b64decode(image_b64),
                    "source": source,
                })

    # --- Fallback: re-run evaluator if no images available ---
    if not images:
        print("\n  No cached or renderable images found.")
        print("  Falling back to re-evaluation (none mode fallback)...")
        images = _rerun_for_images(algorithm)

    if not images:
        print("\n  [No images could be produced for this algorithm]")
        return

    # Print rendering source for each image
    print(f"\n  Images ({len(images)}):")
    for i, img in enumerate(images):
        print(f"    [{i}] {img['title']} — {img['source']}")
        if img["observation"]:
            obs_preview = img["observation"].split("\n")[0][:80]
            print(f"        obs: {obs_preview}")

    # Display with matplotlib
    _show_images(images, algorithm, score)


def _rerun_for_images(algorithm) -> list[dict]:
    """Re-run the evaluator to generate fresh images (none mode fallback).

    Returns:
        List of image dicts, or empty if re-evaluation fails.
    """
    import importlib.util

    from llm4ad.frontend.visualization import VisualizationAPI

    # Import evaluator module to register the renderer
    spec = importlib.util.spec_from_file_location(
        "my_evaluator", str(EVALUATOR_SCRIPT),
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    api = VisualizationAPI(
        generated_dir=(
            algorithm._loaded_from.parent
            if hasattr(algorithm, "_loaded_from")
            else None
        ),
        evaluator_script=EVALUATOR_SCRIPT,
        dataset_dir=DATASET_DIR,
        renderer_modules=[EVALUATOR_SCRIPT],
    )

    behavior_list = api.rerun_and_visualize(algorithm.id)
    images = []
    for bd in behavior_list:
        for viz in bd.visualizations:
            if viz.data_base64:
                images.append({
                    "title": viz.label,
                    "observation": bd.observation,
                    "bytes": base64.b64decode(viz.data_base64),
                    "source": "re-evaluation (none mode fallback)",
                })
    return images


def _show_images(images: list[dict], algorithm, score) -> None:
    """Display images with matplotlib."""
    import matplotlib
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    if matplotlib.get_backend().lower() == "agg":
        plt.switch_backend("TkAgg")

    n = len(images)
    fig, axes = plt.subplots(1, n, figsize=(8 * n, 8))
    if n == 1:
        axes = [axes]

    for ax, img_info in zip(axes, images, strict=False):
        buf = io.BytesIO(img_info["bytes"])
        img = mpimg.imread(buf)
        ax.imshow(img)
        ax.set_title(img_info["title"], fontsize=10)
        ax.axis("off")
        # Add observation and source as annotation
        obs_lines = (
            img_info["observation"].split("\n") if img_info["observation"] else []
        )
        ann_text = "\n".join(obs_lines[:2])
        if ann_text:
            ax.text(
                0.5, -0.08, ann_text,
                transform=ax.transAxes,
                ha="center", va="top",
                fontsize=8, family="monospace",
                bbox={
                    "boxstyle": "round,pad=0.3",
                    "facecolor": "lightyellow",
                    "alpha": 0.8,
                },
            )

    fig.suptitle(
        f"{algorithm.name}  |  score={score}  |  gen={algorithm.generation}",
        fontsize=12, fontweight="bold",
    )
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# 4. Main: interactive or by argument
# ---------------------------------------------------------------------------


def main():
    """Entry point for viewing algorithm behavior visualizations."""
    generated_dir = _find_latest_run()
    run_dir = generated_dir.parent
    print(f"Run directory: {run_dir}")

    algorithms = _index_algorithms(generated_dir)
    if not algorithms:
        print("No algorithms found in", generated_dir)
        sys.exit(1)

    # Parse command-line
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--best":
            best = max(algorithms, key=lambda a: a["score"] or -999)
            print(f"Best algorithm: {best['name']} (score={best['score']})")
            _display_algorithm(best["json_path"])
            return
        else:
            matches = [a for a in algorithms if arg in a["id"]]
            if not matches:
                print(f"No algorithm found matching ID '{arg}'")
                sys.exit(1)
            _display_algorithm(matches[0]["json_path"])
            return

    # Interactive mode
    print(f"\nFound {len(algorithms)} algorithms:\n")
    print(
        f"  {'#':>3}  {'Island':>6}  {'Gen':>3}  {'Score':>10}  "
        f"{'Viz':>4}  {'Operator':<30}  Name",
    )
    sep = "------------------------------"
    print(
        f"  {'---':>3}  {'------':>6}  {'---':>3}  {'----------':>10}  "
        f"{'----':>4}  {sep:<30}  {'----'}",
    )
    for i, alg in enumerate(algorithms):
        score_str = f"{alg['score']:.4f}" if alg["score"] is not None else "    N/A"
        print(
            f"  {i:>3}  {alg['island_id'] or '?':>6}  "
            f"{alg['generation'] or '?':>3}  {score_str:>10}  "
            f"{alg['n_viz']:>4}  {alg['operator']:<30}  {alg['name']}",
        )

    print()
    choice = input("Enter number to view (or 'q' to quit): ").strip()
    if choice.lower() == "q":
        return
    try:
        idx = int(choice)
        _display_algorithm(algorithms[idx]["json_path"])
    except (ValueError, IndexError):
        print(f"Invalid choice: {choice}")


if __name__ == "__main__":
    main()
