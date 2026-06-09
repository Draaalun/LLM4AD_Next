# Sorting Benchmark

End-to-end walkthrough of [`examples/applications/sorting_benchmark_python/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/sorting_benchmark_python). The task is to evolve a Python sorting routine that minimizes execution time and operation counts on a directory of integer-list test cases.

## What evolves

The EVOLVE block lives in `sorting_algorithm/`, the `local_path` declared by `version_control:`:

```python
# EVOLVE_START
def your_sort_function(data):
    """Sort the data list in-place and return (comparisons, swaps)."""
    pass
# EVOLVE_END
```

LLM4AD creates a fresh git worktree per candidate, asks the coder to rewrite this block, then runs the evaluator against each instance under `data/small/`.

## How to run

```bash
cd LLM4AD
uv sync
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

llm4ad run examples/applications/sorting_benchmark_python/config.yaml
```

Expected end-of-run output (abridged):

```text
[bold blue]Running pipeline with config:[/bold blue] examples/applications/sorting_benchmark_python/config.yaml
...
[bold green]Pipeline completed successfully![/bold green] Best score: 0.9842
Best algorithm worktree: sorting_algorithm-abcd1234
Best snapshot: runs/sorting_benchmark_python/<run_id>/best
```

The `best/` directory contains a stable copy of the best worktree, plus `metadata.json` and `summary.txt`. Use `llm4ad evolve check ./runs/<run_id>/best/code` to inspect the EVOLVE block of the winner.

## Config walkthrough

The config is annotated section-by-section. The most relevant fields:

```yaml
project_name: "sorting_benchmark_python"
random_seed: 42

providers:
  - name: "default"
    type: "openai_compatible"
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    model: ${LLM_MODEL}

coder:
  type: "custom"            # naive LLM coder, edits EVOLVE block via diff
  prompt_template: |        # multi-line prompt with {insight}/{project_context} hooks
    ...

evaluator:
  type: "custom"
  module: "sorting_evaluator.py:PythonSortingEvaluator"
  dataset:
    mode: "directory"
    path: "data/small"
  metrics: ["execution_time_ms", "comparisons", "swaps"]

evolution:
  type: "island_ga"
  max_generations: 3
  num_islands: 2
  island_population_size: 4

version_control:
  enabled: true
  local_path: "sorting_algorithm"
```

The bundled `config.yaml` is intentionally short on generations so a smoke run finishes quickly. For real experiments bump `max_generations` to ~30 and `island_population_size` to ~6.

## Evaluator walkthrough

`sorting_evaluator.py:PythonSortingEvaluator` extends `BenchmarkEvaluator`. For each file under `data/small/`, it:

1. Loads the integer list.
2. Spawns `python sort.py "<json>"` inside the worktree (`ctx.project_root`).
3. Parses `{result, comparisons, swaps}` from stdout.
4. Records `execution_time_ms`.
5. Returns an `EvaluationResult` with score = negative of normalized execution time (the framework always maximizes score).

`metrics` includes secondary signals (`comparisons`, `swaps`) so they show up in run summaries even though `score` is single-objective.

## Reading the results

After the run:

```text
runs/sorting_benchmark_python/<run_id>/
├── best/
│   ├── code/                       # winner worktree, ready to inspect
│   ├── metadata.json
│   └── summary.txt
├── state/evolution_state.json      # consumed by the Web UI's rapid analysis view
├── checkpoints/last.json
├── logs/
└── generated/
```

Useful follow-ups:

- `cat runs/.../best/summary.txt` — score progression and metric history.
- `python runs/.../best/code/sort.py "[5,3,8,1,2]"` — try the winning algorithm by hand.
- `llm4ad run config.yaml -r runs/.../checkpoints/last.json` — continue evolution from the last checkpoint.

## Variations to try

- **Larger dataset**: swap `dataset.path` to `data/large/` (generate with the included scripts) for a more realistic benchmark.
- **Multi-objective with MEoH**: change `evolution.type` to `meoh`, list `objective_metrics: ["execution_time_ms", "comparisons"]`, and the orchestrator will track a Pareto front instead of a single best.
- **Free-form coder**: switch `coder.type` to `claude_code` or `opencode` to let an agent edit beyond the marked block (requires the corresponding install extra).

## See also

- [Quick Start](../guides/quickstart.md) — same workflow on a smaller config
- [Evaluators Guide](../guides/evaluators.md) — write your own evaluator
- [Configuration Guide](../guides/configuration.md) — every YAML key
