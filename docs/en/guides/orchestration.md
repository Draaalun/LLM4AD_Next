# Orchestration Methods

In LLM4AD, an *orchestrator* is the component responsible for two decisions:

1. **Which sampler is invoked** at each step — `init`, `mutation`, `crossover`, the DyCA operators `e1` / `e2` / `m1` / `m2` / `summary`, the `meoh_*` family, or any of the multimodal variants;
2. **Which children survive** into the next generation.

All other concerns — Provider, Coder, Evaluator, and the prompts contained in samplers — are shared across orchestrators. This separation is what enables the same codebase to run an Island GA today and a multi-objective EoH tomorrow without further modification.

Three orchestrators are provided out of the box, and together they span the published "iteration + LLM" methods that are presently known. Because the boundary is precisely *sampler choice + survivor selection*, introducing an additional method (FunSearch with reflection, BO-style outer loop, etc.) requires a single class — see [Adding a new orchestrator](#adding-a-new-orchestrator).

## The three built-in orchestrators

| | **Island GA** | **DyCA** | **MEoH** |
|---|---|---|---|
| Search structure | Multi-island population with periodic migration | Single population partitioned by problem-instance cluster | Single population with Pareto archive |
| Parent selection | Per-island tournament / roulette / rank | Cluster-aware: specialist, generalist, and complementary pools | Multi-objective tournament |
| Sampler chain | `init` + `mutation` + `crossover` (+ multimodal) | `init` + `e1` / `e2` / `m1` / `m2` / `summary` / `complementary_cross` (+ multimodal) | `meoh_init` + `meoh_e1` / `meoh_e2` / `meoh_m1` / `meoh_m2` |
| Definition of a generation | One pass over all islands | One pass with optional reclustering | Each `survival()` event |
| Multi-objective | No (single `score`) | No (per-cluster comparison) | **Yes** (Pareto front via `objective_metrics`) |
| Recommended use cases | Quick start, parallel exploration | Heterogeneous instance distributions | Genuine Pareto trade-offs (quality vs. speed, etc.) |
| Extra dependencies | none | `--extra dyca` | `--extra meoh` |
| Reference | [Island GA](island-ga.md) | [DyCA](dyca.md) | [MEoH](meoh.md) |

Selection guidelines:

- **Island GA** — a single, well-understood problem with roughly homogeneous data, where a single winner is the desired outcome. Lowest configuration overhead.
- **DyCA** — datasets that exhibit clearly different regimes (small versus large TSP, easy versus hard ML benchmarks). Suitable when both specialist and generalist algorithms are valuable. Tuning of `n_clusters`, `n_anchors`, and pool sizes is recommended.
- **MEoH** — multiple competing objectives that cannot be reduced to a single weighted score (accuracy vs. compute, tour length vs. runtime, MSE vs. parameter count). Appropriate when a Pareto front is the desired output rather than a single winner.

## Mapping published methods to LLM4AD

LLM4AD's atomicity entails that most published methods correspond to a particular *(orchestrator, sampler set, evaluator type)* triple. The choice is expressed at the component level rather than as a method label.

| Published method | Orchestrator | Sampler chain | Evaluator | Notes |
|---|---|---|---|---|
| **FunSearch** (Romera-Paredes et al., 2024) | `island_ga` | `init_sampler` + `mutation_sampler` only | any `PythonEvaluator` | Set `crossover_rate: 0.0` to align with the original formulation |
| **EoH** (Liu et al., 2024) | `dyca` | `init` + `e1` / `e2` / `m1` / `m2` | any | The DyCA operator names are inherited from EoH |
| **Multimodal EoH** | `dyca` | as above, extended with `multimodal_*` variants | evaluator returning `BehaviorData` | Set `multimodal.enabled: true` and `behavior_storage: "rendered"` |
| **MEoH** (multi-objective EoH) | `meoh` | `meoh_init` + `meoh_e1` / `meoh_e2` / `meoh_m1` / `meoh_m2` | any returning multiple metrics | Set `objective_metrics: [...]` |
| **ReEvo / self-reflection** | any | a custom mutation sampler that injects `error_reflection` cards | any | Enable `memory.auto_extraction.extract_bad: true` |
| **LLM-as-judge benchmarks** | any | default | `LLMJudgeEvaluator` | May be paired with the `mock` provider for inexpensive dry runs |
| **Memory-augmented evolution** | any | default | any | Enable `memory.auto_extraction.enabled: true` together with `extract_good` / `extract_bad` |

Realizing a method involves editing one configuration file rather than forking the codebase. Per-orchestrator field tables are provided in [Configuration § Evolution](configuration.md).

## Configuration outline

The selector is a single field, `evolution.type`:

```yaml
evolution:
  type: "island_ga"   # or "dyca" or "meoh"
  max_generations: 30
  # ... orchestrator-specific fields validated by the matching Pydantic schema
```

`AppConfig` employs a Pydantic discriminated union, so only the fields valid for the selected orchestrator are accepted. Misconfigured fields are rejected at startup rather than silently ignored.

## Side-by-side: TSP

The [TSP example](../examples/tsp.md) ships **all three** configurations against an identical task:

```
examples/applications/tsp_benchmark_python/
├── config.yaml                          # Island GA
├── tsp_dyca_config.yaml                 # DyCA
└── tsp_benchmark_meoh_config.yaml       # MEoH
```

Running the three configurations consecutively is the most direct way to develop intuition regarding which orchestrator best fits a given problem.

## Adding a new orchestrator

An orchestrator is a class with two responsibilities — dispatch and survival:

```python
from llm4ad.orchestrator.base import BaseOrchestrator
from llm4ad.utils.registry import register_orchestrator

@register_orchestrator("my_method")
class MyOrchestrator(BaseOrchestrator):
    async def run(self) -> EvolutionResult:
        ...   # the loop: select samplers, invoke the planner, accept or reject offspring
```

If the new method also requires an additional prompt template, that belongs in a Sampler class (`BasePlanner.register_sampler`) and does not require an orchestrator change. Adding a new evaluator follows the same pattern: subclass `BaseEvaluator` and apply `@register_evaluator`. None of these extensions require modification of unrelated code — this is the [practical consequence of atomicity](../architecture/overview.md#implications-of-atomicity).

## See also

- [Architecture Overview](../architecture/overview.md) — the five components and the role of orchestrators among them.
- [Architecture Data Flow](../architecture/data-flow.md) — what the orchestrator dispatches to during the loop.
- [Island GA](island-ga.md) · [DyCA](dyca.md) · [MEoH](meoh.md) — per-orchestrator configuration fields.
- [Configuration Guide](configuration.md) — the YAML schema.
