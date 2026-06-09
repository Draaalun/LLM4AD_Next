# Multimodal Evolution (MLES) Guide

This guide covers the **Multimodal LLM-based Evolution Strategy (MLES)** feature in LLM4AD:

- Feature overview and core concept
- Quick start
- Architecture and data flow
- Configuration reference
- Frontend integration patterns
- How to add new multimodal tasks
- Existing task reference

## 1. Overview

Traditional LLM-based algorithm evolution (EoH, MEoH) is text-only: the LLM understands algorithm performance through numeric scores and text descriptions, with no visual perception of behavior patterns (trajectory oscillation, path crossings, etc.).

MLES closes this gap by allowing the LLM to **see images of algorithm behavior** (trajectory plots, tour visualizations, etc.) during evolution, enabling visually-grounded improvements.

**Key design principles:**

- **Fully opt-in**: Enable via `multimodal.enabled: true` (default off). Existing text-only workflows are unaffected.
- **Flexible storage**: `behavior_storage` balances disk usage vs. display speed.
- **Frontend-transparent**: The frontend always gets images regardless of storage mode.

## 2. Quick Start

Two changes to an existing text-only YAML config:

### 2.1 Add `multimodal` config block

```yaml
multimodal:
  enabled: true
  behavior_storage: "raw"       # "rendered" | "raw" | "none"
```

### 2.2 Switch to multimodal samplers

```yaml
planner:
  type: "llm_evolution"
  samplers:
    - name: "init_sampler"                    # unchanged
    - name: "multimodal_mutation_sampler"      # replaces mutation_sampler
    - name: "multimodal_crossover_sampler"     # replaces crossover_sampler
```

### 2.3 Use a vision-capable LLM provider

Multimodal samplers embed images in prompts, so the planner provider must support vision input (e.g., `gpt-4o`, `gpt-4o-mini`, `claude-sonnet`).

## 3. Architecture

### 3.1 Data Flow

```
Evaluator (subprocess)
    │
    ├─ score, metrics              (same as text-only)
    └─ BehaviorData                (multimodal addition)
         ├─ observation: str       (text summary)
         └─ visualizations[]
              ├─ data_base64       (pre-rendered PNG, or None)
              ├─ raw_data          (compact data for deferred rendering)
              └─ renderer          (registry name)
                    │
                    ▼
              Dispatcher (aggregates across instances)
                    │
                    ▼
              Orchestrator (attaches to Algorithm object)
                    │
                    ▼
              Multimodal Sampler
                    │
                    ├─ render_visualization(viz)   → base64 PNG
                    ├─ compress_image_base64(...)   → fits LLM token budget
                    └─ embed as ContentPart in ChatMessage
                          │
                          ▼
                      LLM (sees image + text → proposes improvement)
```

### 3.2 Three Storage Modes

`behavior_storage` controls **what gets saved to disk during evolution** — a storage/performance tradeoff, not a visibility switch.

| Mode | What Evaluator Saves | Disk per Instance | Characteristics |
|------|---------------------|-------------------|-----------------|
| `"rendered"` | Pre-rendered base64 PNG | ~40-100 KB | Instant display; larger files |
| `"raw"` | Compact data dict + renderer name | ~1-5 KB | Small files; render on demand |
| `"none"` | Nothing | 0 | Minimal disk; must re-run evaluator |

### 3.3 Silent Degradation Chain (Frontend Image Access)

Regardless of storage mode, the frontend **always** gets an image. `render_visualization()` implements a three-step fallback:

```
1. viz.data_base64 exists?     → return directly         (rendered: instant)
2. viz.raw_data + renderer?    → render on demand, cache  (raw: one-time cost)
3. nothing stored?             → re-run evaluator         (none: slower)
```

### 3.4 Disk File Structure

```
runs/{project_name}/{run_id}/
├── generated/                               # All algorithm artifacts
│   ├── island_0_gen_0_abc123.json           # Algorithm metadata
│   ├── island_0_gen_0_abc123.md             # Human-readable summary
│   ├── island_0_gen_0_abc123_viz_0_0.png    # Behavior image (rendered mode)
│   ├── island_0_gen_0_abc123_raw_0_0.json   # Raw data (raw mode)
│   └── ...
├── output/                                  # Evolution state export
├── worktrees/                               # Algorithm code snapshots
│   └── island_0_gen_0_ind_abc123/
│       └── solve.py                         # Actual algorithm code
└── logs/
```

## 4. Configuration Reference

### MultimodalConfig

```yaml
multimodal:
  enabled: false                    # Master switch (default: false)
  behavior_storage: "rendered"      # Storage mode: "rendered" | "raw" | "none"
  max_images_per_prompt: 3          # Max images per LLM call
  image_max_size_kb: 512            # Auto-compress images beyond this size
  include_observation_text: true    # Include text observations alongside images
```

### PlannerConfig

```yaml
planner:
  type: "llm_evolution"
  mask_evolve_blocks: false         # Whether to mask EVOLVE blocks (default: false)
                                    # false: coder sees existing code, can iterate
                                    # true: coder sees placeholder, forced novel generation
  samplers:
    - name: "init_sampler"
    - name: "multimodal_mutation_sampler"
    - name: "multimodal_crossover_sampler"
  selection_strategy: "weighted"
```

### Algorithm JSON Schema (Key Fields)

```jsonc
{
  "id": "abc123def456",
  "name": "Algorithm Name",
  "description": "...",
  "generation": 3,
  "island_id": 0,
  "parent_ids": ["parent_id_1"],
  "evaluation": {
    "score": -283.45,
    "metrics": { "tour_length": 283.45, "valid_tour": 1.0 }
  },
  "generation_meta": {
    "operator": "multimodal_mutation_sampler",
    "llm_model": "gpt-4o-mini"
  },
  "behavior_data": [
    {
      "observation": "instance_001 | N=10 | Length=283.45",
      "instance_id": "data/small/instance_001.json",
      "visualizations": [
        {
          "label": "TSP Tour",
          "media_type": "image/png",
          "data_base64": null,        // rendered mode: loaded from companion PNG
          "raw_data": { "nodes": [...], "tour": [...] },  // raw mode
          "renderer": "tsp_tour"      // deferred renderer name
        }
      ]
    }
  ]
}
```

## 5. Frontend Integration

### 5.1 VisualizationAPI (Recommended)

`VisualizationAPI` is the standard interface for frontends to access algorithm behavior data:

```python
from llm4ad.frontend.visualization import VisualizationAPI

api = VisualizationAPI(
    generated_dir=Path("runs/my_project/run_001/generated"),
    evaluator_script=Path("my_evaluator.py"),   # needed for none-mode rerun
    dataset_dir=Path("data/"),                  # needed for none-mode rerun
    project_root=Path("my_algorithm/"),          # needed for none-mode rerun
)

# List all algorithms
algorithms = api.list_algorithms()

# Get detail
detail = api.get_algorithm_detail(alg_id)

# Get behavior data (includes storage mode info)
behavior = api.get_algorithm_behavior(alg_id)

# Get image (handles rendered/raw transparently)
image_b64 = api.get_algorithm_image(alg_id, viz_index=0)

# None mode: re-run evaluator
behavior_list = api.rerun_and_visualize(alg_id)
```

### 5.2 Two-Step Fallback Pattern (Frontend Reference)

The standard pattern for frontends to get images, fully implemented in `view_algorithm.py`:

```python
# Step 1: Detect storage mode
def _detect_storage_mode(api, alg_id):
    behavior = api.get_algorithm_behavior(alg_id)
    if not behavior.get("has_behavior"):
        return "none"
    for v in behavior.get("visualizations", []):
        if v["has_rendered_image"]:
            return "rendered"
        if v["has_raw_data"]:
            return "raw"
    return "none"

# Step 2: Get images based on mode
mode = _detect_storage_mode(api, alg_id)
if mode in ("rendered", "raw"):
    # get_algorithm_image() handles both transparently
    image_b64 = api.get_algorithm_image(alg_id, viz_index=0)
else:
    # none mode: re-run evaluator subprocess
    behavior_list = api.rerun_and_visualize(alg_id)
```

### 5.3 Web Frontend HTML Rendering

Images are returned as base64, embed directly in `<img>` tags:

```html
<img src="data:image/png;base64,{image_b64}" alt="Algorithm Behavior" />
```

### 5.4 Reference Implementation

Each multimodal example directory contains `view_algorithm.py` as a complete reference:

- Interactive run selection / `--latest` shortcut
- Interactive algorithm selection / `--best` / `<algorithm_id>` argument
- Auto-detects storage mode and displays it
- Two-step fallback for image retrieval
- matplotlib display

## 6. Adding a New Multimodal Task

### Prerequisites

- A working text-only evaluator (with subprocess isolation)
- A clear visualization idea: what image helps the LLM understand algorithm behavior?

### Step 1: Define Raw Behavior Data

Determine the compact data your algorithm execution produces that can be rendered into an image:

```python
# TSP: tour route
raw_behavior = {
    "nodes": [[x1, y1], [x2, y2], ...],
    "tour": [0, 3, 1, 2, ...],
    "tour_length": 342.15,
}

# LunarLander: trajectory canvas
raw_behavior = {
    "canvas": canvas.tolist(),
    "reward": 150.9,
    "final_state": "Landed safely",
}
```

### Step 2: Modify `_run_episode` to Return Raw Data

```python
def _run_episode(self, ..., capture_behavior=True) -> dict:
    result = {"score": score, "metrics": {...}}
    if capture_behavior:
        result["raw_behavior"] = { ... }  # task-specific compact data
    return result
```

### Step 3: Write a Rendering Function

Standalone function converting raw data to base64 PNG:

```python
def _render_result_image(raw_data: dict) -> str:
    fig, ax = plt.subplots(...)
    # ... draw visualization ...
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
```

### Step 4: Register a Deferred Renderer

Enables `"raw"` storage mode. Place in the evaluator file:

```python
from llm4ad.evaluator.renderer import BaseRenderer

@BaseRenderer.register("my_task_renderer")
class MyTaskRenderer(BaseRenderer):
    def render(self, raw_data: dict, **kwargs) -> str:
        return _render_result_image(raw_data)
```

### Step 5: Build BehaviorData in `evaluate()`

```python
from llm4ad.evaluator.behavior import BehaviorData, BehaviorVisualization

behavior = None
if cfg.behavior_storage != "none":
    if cfg.behavior_storage == "rendered":
        viz = BehaviorVisualization(
            label="My Visualization",
            data_base64=_render_result_image(result["raw_behavior"]),
        )
    elif cfg.behavior_storage == "raw":
        viz = BehaviorVisualization(
            label="My Visualization",
            raw_data=result["raw_behavior"],
            renderer="my_task_renderer",
        )
    behavior = BehaviorData(
        observation=_build_observation_text(result),
        visualizations=[viz],
        instance_id=str(data_path),
    )
return EvaluationResult(score=score, behavior=behavior, ...)
```

### Step 6: Update Subprocess Entry Point

```python
def _subprocess_main():
    input_data = json.loads(sys.argv[1])
    behavior_storage = input_data.get("behavior_storage", "rendered")
    capture = behavior_storage != "none"
    result = evaluator._run_episode(..., capture_behavior=capture)

    # Optimization: render in subprocess for "rendered" mode
    if behavior_storage == "rendered" and result.get("raw_behavior"):
        result["image_base64"] = _render_result_image(result["raw_behavior"])
        del result["raw_behavior"]

    print(json.dumps(result))
```

### Step 7: Write Observation Text Builder

Single-line summary the LLM reads alongside the image:

```python
def _build_observation_text(result: dict) -> str:
    return f"Instance={result['instance']} | Score={result['score']:.4f}"
```

### Step 8: Create YAML Config

```yaml
multimodal:
  enabled: true
  behavior_storage: "raw"

planner:
  samplers:
    - name: "init_sampler"
    - name: "multimodal_mutation_sampler"
    - name: "multimodal_crossover_sampler"
```

### Step 9: Test

```bash
python test_evaluator.py       # verify evaluator + behavior data
python debug_run.py            # full evolution pipeline
python view_algorithm.py       # view behavior visualizations
```

## 7. Existing Task Reference

| Task | Directory | Renderer Name | Raw Data | Observation Format |
|------|-----------|--------------|----------|-------------------|
| LunarLander | `lunarlander_python_multimodal/` | `lunarlander_trajectory` | `{canvas, reward, final_state, seed}` | `Seed=.. \| Reward=.. \| Fuel=..` |
| TSP | `tsp_benchmark_python_multimodal/` | `tsp_tour` | `{nodes, tour, tour_length, n_nodes}` | `inst \| N=.. \| Length=.. \| Time=..` |
| Template | `task_template_python_multimodal/` | `my_task_contour` | `{grid, trajectory, best_point, ...}` | `inst \| Best=.. \| Gap=.. \| Evals=..` |

Each directory contains:

```
my_task_multimodal/
  data/                          # Evaluation instance data
  my_algorithm/                  # EVOLVE-marked code (managed by version control)
  my_evaluator.py                # Multimodal evaluator (key file)
  my_task_benchmark.yaml         # Config with multimodal section
  debug_run.py                   # Run entry point
  test_evaluator.py              # Evaluator test
  view_algorithm.py              # Behavior visualization viewer
```

## 8. Notes and Pitfalls

### Renderer Registration and Lazy Import

Deferred renderers are registered via `@BaseRenderer.register("name")` decorators, which only execute when the evaluator module is imported.

- **During evolution**: The framework auto-imports via the YAML `module` field — no action needed.
- **In standalone scripts**: `VisualizationAPI` auto-imports the `evaluator_script` passed to its constructor.
- If the renderer is not found, `render_visualization()` returns `None` — no crash, the degradation chain continues.

### API Key Security

Never hardcode API keys in YAML configs. Use environment variables:

```yaml
providers:
  - name: "default"
    api_key: ${LLM_API_KEY}
```

### mask_evolve_blocks Configuration

`planner.mask_evolve_blocks` (default `false`) controls whether the coder can see existing EVOLVE block code:

- `false` (recommended): Coder sees full code, can iterate and improve — higher scores.
- `true`: EVOLVE block content replaced with placeholder, forcing novel generation from scratch.

## 9. File Summary

```
src/llm4ad/
  config/schema.py                          # MultimodalConfig, mask_evolve_blocks
  evaluator/
    behavior.py                             # BehaviorData, BehaviorVisualization
    renderer.py                             # BaseRenderer registry, render_visualization()
    dispatcher.py                           # BehaviorData aggregation
  infra/provider/
    base.py                                 # ContentPart (text + image)
    anthropic.py                            # Multimodal message serialization
    openai_compatible.py                    # Multimodal message serialization
  planner/
    base.py                                 # Algorithm.behavior_data, serialization
    llm_evolution.py                        # mask_evolve_blocks config
    sampler/
      prompt_templates.py                   # Multimodal prompt builders
      multimodal_mutation_sampler.py        # Image-aware mutation
      multimodal_crossover_sampler.py       # Image-aware crossover
  utils/image_utils.py                      # Image compression for LLM prompts
  frontend/visualization.py                 # VisualizationAPI

examples/applications/
  lunarlander_python_multimodal/            # LunarLander reference implementation
  tsp_benchmark_python_multimodal/          # TSP reference implementation
  task_template_python_multimodal/          # Starter template for new tasks
```
