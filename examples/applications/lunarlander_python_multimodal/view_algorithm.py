"""View LunarLander algorithm behavior with automatic storage-mode detection.

Uses the VisualizationAPI to auto-detect which ``behavior_storage`` mode
was used during evolution and applies the correct rendering strategy:

  - **rendered**: cached PNG on disk, returned directly.
  - **raw**: structured data + registered renderer, deferred render.
  - **none**: no data saved, re-runs evaluator subprocess.

Two-step fallback (reference pattern for any frontend):

  1. ``get_algorithm_image()`` -- handles *rendered* and *raw* transparently.
  2. ``rerun_and_visualize()``  -- for *none* mode.

Usage:
    python view_algorithm.py                   # interactive
    python view_algorithm.py <algorithm_id>    # show specific algorithm
    python view_algorithm.py --best            # show the best-scoring one
    python view_algorithm.py --latest          # skip run selection
"""

import base64
import io
import sys
from pathlib import Path

import matplotlib
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

from llm4ad.frontend.visualization import VisualizationAPI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EXAMPLE_DIR = Path(__file__).parent
RUNS_ROOT = EXAMPLE_DIR / "runs"
EVALUATOR_SCRIPT = EXAMPLE_DIR / "lunarlander_evaluator.py"
DATASET_DIR = EXAMPLE_DIR / "data" / "train"
PROJECT_ROOT = EXAMPLE_DIR / "policy"


# ---------------------------------------------------------------------------
# Run selection
# ---------------------------------------------------------------------------


def _find_generated_dir() -> Path:
    """Interactively select a run directory, or use --latest.

    Returns:
        Path to the ``generated/`` directory of the chosen run.
    """
    candidates = sorted(
        RUNS_ROOT.rglob("generated"), key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        print("No runs found under", RUNS_ROOT)
        sys.exit(1)

    if "--latest" in sys.argv:
        return candidates[-1]

    if len(candidates) == 1:
        return candidates[0]

    print("Available runs:\n")
    for i, gen_dir in enumerate(candidates):
        run_dir = gen_dir.parent
        n_json = len(list(gen_dir.glob("*.json")))
        print(f"  [{i}] {run_dir.relative_to(RUNS_ROOT)}  ({n_json} algorithms)")

    print()
    choice = input(
        f"Select run [0-{len(candidates) - 1}] "
        f"(default: {len(candidates) - 1} = latest): ",
    ).strip()

    if choice == "":
        return candidates[-1]
    try:
        idx = int(choice)
        return candidates[idx]
    except (ValueError, IndexError):
        print(f"Invalid choice: {choice}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Storage mode detection
# ---------------------------------------------------------------------------


def _detect_storage_mode(api: VisualizationAPI, alg_id: str) -> str:
    """Detect the behavior storage mode for an algorithm.

    Args:
        api: Initialized VisualizationAPI instance.
        alg_id: Algorithm identifier.

    Returns:
        One of ``"rendered"``, ``"raw"``, or ``"none"``.
    """
    behavior = api.get_algorithm_behavior(alg_id)
    if not behavior.get("has_behavior"):
        return "none"
    for v in behavior.get("visualizations", []):
        if v["has_rendered_image"]:
            return "rendered"
        if v["has_raw_data"]:
            return "raw"
    return "none"


# ---------------------------------------------------------------------------
# Image retrieval (two-step fallback)
# ---------------------------------------------------------------------------


def _get_images(
    api: VisualizationAPI,
    alg_id: str,
    detail: dict,
    mode: str,
) -> list[dict]:
    """Retrieve behavior images using the appropriate strategy.

    Args:
        api: Initialized VisualizationAPI instance.
        alg_id: Algorithm identifier.
        detail: Detail dict from ``get_algorithm_detail()``.
        mode: Detected storage mode ("rendered", "raw", or "none").

    Returns:
        List of image dicts with 'title', 'observation', 'bytes', 'source'.
    """
    images: list[dict] = []

    if mode in ("rendered", "raw"):
        source = "cached PNG" if mode == "rendered" else "deferred render"
        for img_meta in detail["images"]:
            image_b64 = api.get_algorithm_image(
                alg_id, viz_index=img_meta["index"],
            )
            if image_b64:
                obs = (
                    detail["observations"][img_meta["index"]]
                    if img_meta["index"] < len(detail["observations"])
                    else ""
                )
                images.append({
                    "title": img_meta["label"],
                    "observation": obs,
                    "bytes": base64.b64decode(image_b64),
                    "source": source,
                })

    if not images:
        print("  Falling back to re-evaluation (subprocess)...")
        behavior_list = api.rerun_and_visualize(alg_id)
        for bd in behavior_list:
            for viz in bd.visualizations:
                if viz.data_base64:
                    images.append({
                        "title": viz.label,
                        "observation": bd.observation,
                        "bytes": base64.b64decode(viz.data_base64),
                        "source": "re-evaluation",
                    })

    return images


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def _show_images(images: list[dict], title: str) -> None:
    """Display images with matplotlib.

    Args:
        images: List of dicts with 'title', 'observation', 'bytes' keys.
        title: Figure suptitle.
    """
    if not images:
        print("  [No images to display]")
        return

    if matplotlib.get_backend().lower() == "agg":
        plt.switch_backend("TkAgg")

    n = len(images)
    fig, axes = plt.subplots(1, n, figsize=(7 * n, 6))
    if n == 1:
        axes = [axes]

    for ax, img_info in zip(axes, images, strict=False):
        buf = io.BytesIO(img_info["bytes"])
        img = mpimg.imread(buf)
        ax.imshow(img)
        ax.set_title(img_info["title"], fontsize=10)
        ax.axis("off")
        if img_info.get("observation"):
            obs_lines = img_info["observation"].split("\n")
            ax.text(
                0.5, -0.08, "\n".join(obs_lines[:2]),
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8, family="monospace",
                bbox={
                    "boxstyle": "round,pad=0.3",
                    "facecolor": "lightyellow",
                    "alpha": 0.8,
                },
            )

    fig.suptitle(title, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Algorithm detail + image display
# ---------------------------------------------------------------------------


def _display_algorithm(api: VisualizationAPI, alg_id: str) -> None:
    """Show detail and behavior images for a single algorithm.

    Args:
        api: Initialized VisualizationAPI instance.
        alg_id: Algorithm identifier.
    """
    detail = api.get_algorithm_detail(alg_id)
    print(f"\n{'=' * 60}")
    print(f"  Algorithm : {detail['name']}")
    print(f"  ID        : {detail['id']}")
    print(f"  Score     : {detail['score']}")
    print(f"  Operator  : {detail['operator']}  |  Gen: {detail['generation']}")
    print(f"  Parents   : {detail['parent_ids'] or 'none (initial)'}")
    print(f"{'=' * 60}")

    desc = detail.get("description", "")
    if desc:
        print(f"\n  Description:\n  {desc[:200]}...")

    # Detect storage mode
    mode = _detect_storage_mode(api, alg_id)
    mode_desc = {
        "rendered": "rendered (cached PNG on disk)",
        "raw": "raw (deferred render via registry)",
        "none": "none (no data stored, will re-evaluate)",
    }
    print(f"\n  Storage mode: {mode_desc[mode]}")

    # Get images
    images = _get_images(api, alg_id, detail, mode)

    if not images:
        print("\n  [No images could be produced for this algorithm]")
        return

    print(f"\n  Images ({len(images)}):")
    for i, img in enumerate(images):
        print(f"    [{i}] {img['title']} -- source: {img['source']}")
        if img["observation"]:
            obs_preview = img["observation"].split("\n")[0][:80]
            print(f"        obs: {obs_preview}")

    _show_images(
        images,
        f"{detail['name']}  |  score={detail['score']}  |  mode={mode}",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    """Entry point: interactive or CLI-driven algorithm viewer."""
    generated_dir = _find_generated_dir()
    run_dir = generated_dir.parent
    print(f"Run directory: {run_dir}\n")

    api = VisualizationAPI(
        generated_dir=generated_dir,
        evaluator_script=EVALUATOR_SCRIPT,
        dataset_dir=DATASET_DIR,
        project_root=PROJECT_ROOT,
    )

    algorithms = api.list_algorithms()
    if not algorithms:
        print("No algorithms found in", generated_dir)
        sys.exit(1)

    # --- CLI argument handling ---
    cli_args = [a for a in sys.argv[1:] if a != "--latest"]
    if cli_args:
        arg = cli_args[0]
        if arg == "--best":
            scored = [a for a in algorithms if a["score"] is not None]
            if not scored:
                print("No scored algorithms found")
                sys.exit(1)
            best = max(scored, key=lambda a: a["score"])
            print(f"Best algorithm: {best['name']} (score={best['score']:.4f})")
            _display_algorithm(api, best["id"])
            return
        else:
            # Treat as algorithm_id substring
            matches = [a for a in algorithms if arg in a["id"]]
            if not matches:
                print(f"No algorithm found matching ID '{arg}'")
                sys.exit(1)
            _display_algorithm(api, matches[0]["id"])
            return

    # --- Interactive mode ---
    print(f"Found {len(algorithms)} algorithms:\n")
    print(
        f"  {'#':>3}  {'Island':>6}  {'Gen':>3}  {'Score':>8}  "
        f"{'Imgs':>4}  {'Operator':<30}  Name",
    )
    print(
        f"  {'---':>3}  {'------':>6}  {'---':>3}  {'--------':>8}  "
        f"{'----':>4}  {'------------------------------':<30}  {'----'}",
    )
    for i, alg in enumerate(algorithms):
        score_str = (
            f"{alg['score']:.4f}" if alg["score"] is not None else "  N/A"
        )
        print(
            f"  {i:>3}  {alg['island_id'] or '?':>6}  "
            f"{alg['generation'] or '?':>3}  {score_str:>8}  "
            f"{alg['n_images']:>4}  {alg['operator']:<30}  {alg['name']}",
        )

    print()
    while True:
        choice = input("Enter number to view (or 'q' to quit): ").strip()
        if choice.lower() == "q":
            break
        try:
            idx = int(choice)
            _display_algorithm(api, algorithms[idx]["id"])
        except (ValueError, IndexError):
            print(f"Invalid choice: {choice}")


if __name__ == "__main__":
    main()
