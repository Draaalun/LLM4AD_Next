# Frontend Integration Guide

How to display algorithm behavior visualizations from LLM4AD runs.

## Directory Structure

```
runs/{project_name}/{run_id}/
├── generated/                          # All algorithm artifacts
│   ├── island_0_gen_0_abc123.json      # Algorithm metadata
│   ├── island_0_gen_0_abc123.md        # Human-readable summary
│   ├── island_0_gen_0_abc123_viz_0_0.png  # Trajectory image (rendered mode)
│   ├── island_0_gen_0_abc123_raw_0_0.json # Canvas data (raw mode)
│   └── ...
├── output/                             # Evolution state export
├── worktrees/                          # Algorithm code snapshots
│   ├── island_0_gen_0_ind_abc123/
│   │   └── choose_action.py            # The actual policy code
│   └── ...
└── logs/
```

## Behavior Storage Modes

Configure via `multimodal.behavior_storage` in the YAML config:

| Mode | What's saved | Disk size | Display speed | Config |
|------|-------------|-----------|---------------|--------|
| `"rendered"` | PNG images (`_viz_*.png`) | Largest | Instant — load PNG | `behavior_storage: "rendered"` |
| `"raw"` | Canvas JSON (`_raw_*.json`) | ~Same as PNG | On-demand render via `BaseRenderer` | `behavior_storage: "raw"` |
| `"none"` | Nothing | Smallest | Requires re-evaluation | `behavior_storage: "none"` |

### How each mode works

**rendered** (default): The evaluator produces a pre-rendered base64 PNG
image. `Algorithm.write()` extracts it to a companion `.png` file.
`Algorithm.load()` rehydrates it back. Fastest for display.

**raw**: The evaluator produces compact JSON-serializable data (e.g.,
the composited canvas as nested Python lists). `Algorithm.write()` saves
it to a companion `.json` file. When the frontend calls
`get_algorithm_image()`, the registered `BaseRenderer` converts the raw
data into a PNG on demand. Requires importing the renderer module.

**none**: No behavior data is saved at all. The frontend must call
`rerun_and_visualize()` to spawn the evaluator subprocess and produce
fresh trajectory images. Smallest disk footprint.

## JSON Schema (Key Fields)

```jsonc
{
  "id": "abc123def456",           // 12-char hex, unique identifier
  "name": "Algorithm Name",
  "description": "What this algorithm does...",
  "generation": 3,
  "island_id": 0,
  "parent_ids": ["parent_id_1"],  // Empty for initial generation

  "evaluation": {
    "score": 0.5304,              // Normalized score (higher = better)
    "metrics": {
      "episode_reward": 150.9,
      "fuel_consumed": 126,
      "success": 0.0
    }
  },

  "generation_meta": {
    "operator": "multimodal_mutation_sampler",  // Which sampler created this
    "llm_model": "gpt-4o-mini",
    "temperature": 0.7
  },

  "behavior_data": [              // One entry per evaluation instance
    {
      "observation": "Seed=6 | Reward=150.9 | State=Timed out",
      "instance_id": "/path/to/instance_001.json",
      "visualizations": [
        {
          "label": "Lander Trajectory",
          "media_type": "image/png",
          "data_base64": null,    // Stripped in JSON; image is in PNG file
          "raw_data": {
            "_saved_image_file": "island_0_gen_0_abc123_viz_0_0.png"
          }
        }
      ]
    }
  ],

  "worktree": {
    "path": "/absolute/path/to/worktree",
    "commit_hash": "8dd0e16..."
  }
}
```

## Three Image Access Strategies

### Strategy 1: Read PNG directly (fastest)

The JSON's `_saved_image_file` points to a PNG in the same directory.

```python
# Direct file access — no API needed
png_path = generated_dir / viz["raw_data"]["_saved_image_file"]
image_bytes = png_path.read_bytes()

# For web: serve as static file
# GET /api/runs/{run_id}/generated/{filename}.png
```

### Strategy 2: Via VisualizationAPI (handles lazy rendering)

```python
from llm4ad.frontend.visualization import VisualizationAPI

api = VisualizationAPI(generated_dir=Path("runs/.../generated"))

# Returns base64 string — rehydrates from PNG automatically
image_b64 = api.get_algorithm_image("abc123", viz_index=0)

# For web: return as data URL
# <img src="data:image/png;base64,{image_b64}" />
```

### Strategy 3: Re-evaluate (when no cached data exists)

```python
api = VisualizationAPI(
    generated_dir=Path("runs/.../generated"),
    evaluator_script=Path("lunarlander_evaluator.py"),
    dataset_dir=Path("data/train"),
)

# Spawns evaluator subprocess, returns fresh BehaviorData
behavior_list = api.rerun_and_visualize("abc123")

for bd in behavior_list:
    for viz in bd.visualizations:
        image_b64 = viz.data_base64  # Fresh base64 image
```

## API Reference

### `VisualizationAPI(generated_dir, evaluator_script=None, dataset_dir=None, renderer_modules=None)`

Constructor. Point it at a run's `generated/` directory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `generated_dir` | `Path` | Path to `runs/{project}/{run_id}/generated/` |
| `evaluator_script` | `Path \| None` | Path to evaluator .py for re-evaluation |
| `dataset_dir` | `Path \| None` | Path to `data/train/` for instance discovery |
| `renderer_modules` | `list[str \| Path] \| None` | Renderer modules to import for deferred rendering (raw mode) |

```python
# For "raw" mode, import the evaluator module (which also registers the renderer):
api = VisualizationAPI(
    generated_dir=Path("runs/.../generated"),
    renderer_modules=[Path("lunarlander_evaluator.py")],
)
```

### `list_algorithms(island_id=None, generation=None) -> list[dict]`

List all algorithms with lightweight metadata (no image loading).

```python
algorithms = api.list_algorithms()
# Returns: [{id, name, score, generation, island_id, operator, n_images, has_behavior}, ...]

# Filter by island or generation:
island_0_gen_3 = api.list_algorithms(island_id=0, generation=3)
```

### `get_algorithm_detail(algorithm_id) -> dict`

Full metadata for one algorithm. Call when user clicks a row.

```python
detail = api.get_algorithm_detail("abc123")
# Returns: {id, name, description, score, generation, island_id,
#           operator, parent_ids, observations: [str], images: [{index, label, available}]}
```

### `get_algorithm_image(algorithm_id, viz_index=0) -> str | None`

Get a single base64 image. Handles PNG rehydration and lazy rendering.

```python
image_b64 = api.get_algorithm_image("abc123", viz_index=0)
if image_b64:
    # Render: <img src="data:image/png;base64,{image_b64}" />
else:
    # Show "Re-evaluate" button → call rerun_and_visualize()
```

### `rerun_and_visualize(algorithm_id, timeout=120) -> list[BehaviorData]`

Re-run the policy evaluation from scratch. Returns fresh behavior data.

```python
behaviors = api.rerun_and_visualize("abc123")
for bd in behaviors:
    print(bd.observation)           # Text description
    for viz in bd.visualizations:
        b64 = viz.data_base64       # Fresh base64 PNG
```

## Frontend Flow

```
User opens run page
    │
    ▼
list_algorithms()  →  Render algorithm table
    │
    ▼ (user clicks a row)
    │
get_algorithm_detail(id)  →  Show metadata panel
    │
    ▼ (for each image in detail.images)
    │
    ├── image.available == True
    │   └── get_algorithm_image(id, index)
    │       ├── Has base64 (rendered mode) → <img src="data:...">
    │       └── Has raw_data + renderer (raw mode) → render on demand → <img src="data:...">
    │
    └── image.available == False (none mode)
        └── Show "Re-evaluate" button
            │
            ▼ (user clicks)
            │
            rerun_and_visualize(id)  →  Display fresh images
```
