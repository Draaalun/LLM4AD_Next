# Orchestrator API

`llm4ad.orchestrator` assembles the planner, coder, and evaluator into an evolution loop. Three orchestrators ship today, each implementing a different search strategy.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `BaseOrchestrator` | Abstract orchestrator; subclass and call `register_orchestrator("name")` | `src/llm4ad/orchestrator/base.py` |
| `IslandGAOrchestrator` | Classic island genetic algorithm (independent subpopulations + periodic migration) | `src/llm4ad/orchestrator/island_ga.py` |
| `DyCAOrchestrator` | Dynamic clustering adaptive evolution (cluster instances, multi-pool allocation) | `src/llm4ad/orchestrator/dyca.py` |
| `MEoHOrchestrator` | Multi-objective Evolution of Heuristics with survival-based generations | `src/llm4ad/orchestrator/meoh.py` |
| `MEoHPopulation` | MEoH's multi-objective population manager (non-dominated sort, crowding) | `src/llm4ad/orchestrator/meoh_population.py` |
| `EvolutionResult`, `EvolutionCheckpoint` | Run-end and checkpoint structures | `src/llm4ad/orchestrator/base.py` |
| `EvolutionState`, `StateTracker` | Accumulated population, best individual, history, trajectory | `src/llm4ad/infra/state.py` |
| `EmbeddingClient` | Orchestrator-internal embedding client used for trajectory analysis | `src/llm4ad/orchestrator/embedding_client.py` |
| `format_duration_ms` | Format milliseconds as `1h 2min 3s` | `src/llm4ad/orchestrator/base.py` |

## Running an evolution

The simplest path is the top-level entry point:

```python
from llm4ad import LLM4AD

llm4ad = LLM4AD("config.yaml")
result = await llm4ad.run()               # wires up the orchestrator internally
print(result.best_individual.score)
```

Direct orchestrator use:

```python
from llm4ad.orchestrator.base import BaseOrchestrator

BaseOrchestrator.discover("llm4ad.orchestrator")
orch = BaseOrchestrator.create(
    "dyca",
    config=app_config,
    planner=planner,
    coder=coder,
    evaluator=evaluator,
)
result: EvolutionResult = await orch.run()
```

## EvolutionResult fields

| Field | Meaning |
|---|---|
| `state` | `EvolutionState` enum (`completed`, `failed`, `stopped`, …) |
| `best_individual` | Best `Algorithm` for a single-objective run |
| `final_population` | Final population for single-objective; elitist archive for multi-objective |
| `final_generation` | Last advanced generation |
| `total_evaluations` | Total number of evaluation calls |
| `metadata.objective_metrics` | Objective list for multi-objective runs |
| `metadata.elitist_archive` | Multi-objective Pareto archive (set by MEoH) |
| `metadata.per_objective_best` | Per-objective best values for multi-objective runs |
| `duration_seconds` | Total wall-clock time |

## Checkpointing + resume

`evolution.checkpoint_interval` controls how often an `EvolutionCheckpoint` is written. To resume:

```bash
llm4ad run config.yaml -r ./runs/proj/run-2026-05-13/checkpoints/last.json
```

Or in Python:

```python
result = await llm4ad.run(resume_from_checkpoint="checkpoints/last.json")
```

## `best/` export

At end of run, `LLM4AD.run()` writes a stable snapshot of the best individual (or, for multi-objective, the elitist archive) into the `best/` subdirectory of the run directory. The CLI prints the path on completion (see `cli.py:184`). Multi-objective runs additionally produce `best/pareto/<idx>/` per archive entry.

## Orchestrator highlights

| Orchestrator | Parent selection | Offspring generation | When to use |
|---|---|---|---|
| `island_ga` | Per-island selection | Single-parent mutation, two-parent crossover | Simple multimodal search; parallel and explainable |
| `dyca` | Cluster-aware selection | E1/E2/M1/M2/summary/complementary operators | Heterogeneous instance distribution; specialist algorithms wanted |
| `meoh` | Multi-objective parent selection | meoh_e1/e2/m1/m2 | True multi-objective problems where you need a Pareto front |

See [Orchestration Methods Overview](../guides/orchestration.md) for the decision matrix.

## See also

- [Orchestration Overview](../guides/orchestration.md)
- [DyCA](../guides/dyca.md) · [MEoH](../guides/meoh.md) · [Island GA](../guides/island-ga.md)
- Source of truth: `src/llm4ad/orchestrator/`
