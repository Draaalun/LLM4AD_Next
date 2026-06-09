# Frontend Integration Guide — TSP Multimodal

How to display TSP algorithm behavior visualizations from LLM4AD runs.

## Directory Structure

```
runs/{project_name}/{run_id}/
├── generated/                          # All algorithm artifacts
│   ├── island_0_gen_0_abc123.json      # Algorithm metadata
│   ├── island_0_gen_0_abc123.md        # Human-readable summary
│   ├── island_0_gen_0_abc123_viz_0_0.png  # Tour image (rendered mode)
│   ├── island_0_gen_0_abc123_raw_0_0.json # Tour data (raw mode)
│   └── ...
├── output/                             # Evolution state export
├── worktrees/                          # Algorithm code snapshots
│   ├── island_0_gen_0_ind_abc123/
│   │   └── solve.py                    # The actual TSP solver code
│   └── ...
└── logs/
```

## Behavior Storage Modes

Configure via `multimodal.behavior_storage` in the YAML config:

| Mode | What's saved | Disk size | Display speed | Config |
|------|-------------|-----------|---------------|--------|
| `"rendered"` | PNG images (`_viz_*.png`) | ~40 KB/image | Instant — load PNG | `behavior_storage: "rendered"` |
| `"raw"` | Tour JSON (`_raw_*.json`) | ~1 KB/tour | On-demand render via `BaseRenderer` | `behavior_storage: "raw"` |
| `"none"` | Nothing | 0 | Requires re-evaluation | `behavior_storage: "none"` |

Note: TSP raw data is very compact (just nodes + tour indices), making `"raw"` mode significantly smaller than `"rendered"`.

### Raw data schema

```json
{
    "nodes": [[44.82, 26.88], [2.16, 33.80], ...],
    "tour": [0, 3, 1, 2, 5, 7, 4, 6, 8, 9],
    "tour_length": 283.45,
    "n_nodes": 10
}
```

## JSON Schema (Key Fields)

```jsonc
{
  "id": "abc123def456",           // 12-char hex, unique identifier
  "name": "Algorithm Name",
  "description": "What this algorithm does...",
  "generation": 3,
  "island_id": 0,
  "parent_ids": ["parent_id_1"],

  "evaluation": {
    "score": -283.45,             // Negative tour length (lower = shorter tour)
    "metrics": {
      "tour_length": 283.45,
      "valid_tour": 1.0,
      "execution_time_ms": 12.3
    }
  },

  "generation_meta": {
    "operator": "multimodal_mutation_sampler",
    "llm_model": "gpt-4o-mini",
    "temperature": 0.7
  },

  "behavior_data": [              // One entry per evaluation instance
    {
      "observation": "instance_001 | N=10 | Length=283.45 | Time=12.3ms | Valid=Yes",
      "instance_id": "/path/to/data/small/instance_001.json",
      "visualizations": [
        {
          "label": "TSP Tour",
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

```python
png_path = generated_dir / viz["raw_data"]["_saved_image_file"]
image_bytes = png_path.read_bytes()
```

### Strategy 2: Via VisualizationAPI (handles lazy rendering)

```python
from llm4ad.frontend.visualization import VisualizationAPI

api = VisualizationAPI(
    generated_dir=Path("runs/.../generated"),
    renderer_modules=[Path("tsp_evaluator.py")],  # For raw mode
)

image_b64 = api.get_algorithm_image("abc123", viz_index=0)
# <img src="data:image/png;base64,{image_b64}" />
```

### Strategy 3: Re-evaluate (when no cached data exists)

```python
api = VisualizationAPI(
    generated_dir=Path("runs/.../generated"),
    evaluator_script=Path("tsp_evaluator.py"),
    dataset_dir=Path("data/small"),
)

behavior_list = api.rerun_and_visualize("abc123")
for bd in behavior_list:
    for viz in bd.visualizations:
        image_b64 = viz.data_base64  # Fresh base64 PNG
```

## API Reference

### `VisualizationAPI(generated_dir, evaluator_script=None, dataset_dir=None, renderer_modules=None)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `generated_dir` | `Path` | Path to `runs/{project}/{run_id}/generated/` |
| `evaluator_script` | `Path \| None` | Path to evaluator .py for re-evaluation |
| `dataset_dir` | `Path \| None` | Path to `data/small/` for instance discovery |
| `renderer_modules` | `list[str \| Path] \| None` | Renderer modules for deferred rendering |

### `list_algorithms(island_id=None, generation=None) -> list[dict]`

### `get_algorithm_detail(algorithm_id) -> dict`

### `get_algorithm_image(algorithm_id, viz_index=0) -> str | None`

### `rerun_and_visualize(algorithm_id, timeout=120) -> list[BehaviorData]`

## Frontend Flow

```
User opens run page
    |
    v
list_algorithms()  ->  Render algorithm table
    |
    v (user clicks a row)
    |
get_algorithm_detail(id)  ->  Show metadata panel
    |
    v (for each image in detail.images)
    |
    +-- image.available == True
    |   +-- get_algorithm_image(id, index)
    |       +-- Has base64 (rendered mode) -> <img src="data:...">
    |       +-- Has raw_data + renderer (raw mode) -> render on demand
    |
    +-- image.available == False (none mode)
        +-- Show "Re-evaluate" button
            |
            v (user clicks)
            |
            rerun_and_visualize(id)  ->  Display fresh tour images
```
