# Infrastructure API

`llm4ad.infra` is the low-level infrastructure shared across modules. Most users do not import directly from here, but the entry points become relevant whenever orchestrators, evaluators, or custom integrations need state, timing, version control, or repo analysis.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `StateTracker`, `EvolutionState` | Per-generation accumulation of population, best, history, trajectory | `src/llm4ad/infra/state.py` |
| `BestExporter` | `best/` exporter — writes the final-best snapshot to a stable path | `src/llm4ad/infra/best_exporter.py` |
| `ExecutionTiming`, `TimingPhase` | Fine-grained timing for provider / coder / evaluator calls | `src/llm4ad/infra/timing.py` |
| `BaseVersionControl`, `WorktreeInfo`, `VersionControlConfig` | Git worktree management (isolation of concurrent individuals) | `src/llm4ad/infra/version_control/` |
| `inspect_path`, `clean_path`, `AnalyzedRepository` | EVOLVE-marker detection + removal (powers `llm4ad evolve check/clean`) | `src/llm4ad/infra/repo_analyzer/` |
| `EvolveDetector` | EVOLVE marker scanner/parser (detects nested, unbalanced markers) | `src/llm4ad/infra/repo_analyzer/detector.py` |
| `BaseProvider`, `OpenAICompatibleProvider`, … | LLM providers — covered separately on the [Provider API](provider.md) page | `src/llm4ad/infra/provider/` |
| `BaseRunMonitor` | Hook for run-progress monitors (CLI progress, Web UI streaming) | `src/llm4ad/infra/monitor/` |

## State tracking

```python
from llm4ad.infra.state import StateTracker

tracker = StateTracker()
tracker.record_individual(algorithm, evaluation_result)
tracker.record_generation(gen_index, best_so_far)
tracker.save_checkpoint(path="checkpoints/gen10.json")
```

`StateTracker` persists the trajectory to `state/evolution_state.json` in the run directory; the frontend Web UI's "rapid evolutionary analysis" reads this file to render trajectories.

## Timing

`ExecutionTiming` is a lightweight structure attached to every LLM call, coder call, and evaluator result. It breaks total wall-clock time into phases (request construction, network, streaming parse, post-processing).

```python
from llm4ad.infra.timing import ExecutionTiming

timing = ExecutionTiming()
with timing.phase("network"):
    response = await provider.chat(messages)
print(timing.total_ms, timing.phases)
```

See [Timing & Metrics](../guides/timing-metrics.md).

## Repository analysis (EVOLVE markers)

```python
from llm4ad.infra.repo_analyzer import inspect_path, clean_path

result = inspect_path("examples/applications/sorting_benchmark_python")
print(result.summary["blocks"], result.active_block_id)

# Dry-run: report which lines would be removed, no writes
clean = clean_path("examples/applications/sorting_benchmark_python")
# Actually rewrite files:
clean = clean_path("examples/applications/sorting_benchmark_python", apply=True)
```

In CLI form: `llm4ad evolve check` and `llm4ad evolve clean` (see [CLI Reference](../guides/cli.md#evolve)).

## Version control / worktrees

`BaseVersionControl` creates a throwaway git worktree per candidate algorithm so the main branch stays clean. `VersionControlConfig` is configured under `version_control:` in YAML (defaults are typically fine).

## Embeddings

Embedding support is rooted in `llm4ad.orchestrator` (`EmbeddingClient`, `embedding_utils.py`), but the backend providers are still registered in `llm4ad.infra.provider`. Batched embeddings and the `local` two-endpoint mode are covered in [Embeddings & Trajectory](../guides/embeddings.md).

## See also

- [Configuration Guide](../guides/configuration.md) — `version_control:`, `logging:`, `workspace:`
- [Timing & Metrics](../guides/timing-metrics.md) — detailed timing
- Source of truth: `src/llm4ad/infra/`
