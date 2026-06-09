# Planner API

`llm4ad.planner` proposes the next algorithm to evolve. A planner combines an LLM provider, a chain of samplers, and the current evolution state to emit `Algorithm` candidates. Two planners ship today; both feed orchestrators registered in `llm4ad.orchestrator`.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `BasePlanner` | Abstract planner; subclass and call `register_planner("name")` | `src/llm4ad/planner/base.py` |
| `LLMEvolutionPlanner` | Default planner for Island GA and DyCA (init / mutation / crossover with optional multimodal variants) | `src/llm4ad/planner/llm_evolution.py` |
| `MEoHEvolutionPlanner` | Survival-based planner for the MEoH orchestrator | `src/llm4ad/planner/meoh_evolution.py` |
| `Algorithm`, `AlgorithmInsight`, `InsightType` | Proposal envelope passed to coder + evaluator | `src/llm4ad/planner/base.py` |
| `CodeArtifact`, `GenerationMetadata` | Code-side payload of an `Algorithm` (full or unified-diff) | `src/llm4ad/planner/base.py` |

## Sampler chain

Each planner runs a chain of samplers registered under `llm4ad.planner.sampler`. The sampler chosen at every step depends on the orchestrator and the operator the planner is invoking.

| Sampler family | Used by | Purpose |
|---|---|---|
| `init_sampler` / `multimodal_init_sampler` | All | Generate the initial population |
| `mutation_sampler` / `multimodal_mutation_sampler` | Island GA, DyCA | Local perturbation of one parent |
| `crossover_sampler` / `multimodal_crossover_sampler` | Island GA, DyCA | Recombine two parents |
| `e1_sampler`, `e2_sampler`, `m1_sampler`, `m2_sampler`, `summary_sampler`, `complementary_cross_sampler` | DyCA | Cluster-aware operators (see [DyCA](../guides/dyca.md)) |
| `meoh_init_sampler`, `meoh_e1_sampler`, `meoh_e2_sampler`, `meoh_m1_sampler`, `meoh_m2_sampler` | MEoH | Multi-objective operators (see [MEoH](../guides/meoh.md)) |

The active samplers per run are listed under `planner.samplers` in YAML. Validation will reject a `multimodal_*` sampler when `multimodal.enabled` is `false`.

## Generating a single proposal

```python
from llm4ad.planner.base import BasePlanner

BasePlanner.discover("llm4ad.planner")
planner = BasePlanner.create("llm_evolution", config=app_config, provider=provider, ...)

algorithm = await planner.propose(
    operator="mutation",
    parents=[parent_individual],
    state_tracker=state_tracker,
)
```

The returned `Algorithm` is the unit the orchestrator hands to the [Coder](coder.md) and then to the [Evaluator](evaluator.md). Its `code_artifacts` may be in `full` or `diff` content mode; `apply_unified_diff` (see [Utilities](utils.md)) reassembles the source when working in diff mode.

## Insight types

`InsightType` records why a proposal was created — `INITIAL`, `MUTATION`, `CROSSOVER`, `REFLECTION`. It travels with the algorithm through evaluation and into the state tracker, so logs and visualizations can attribute improvements back to the operator that produced them.

## See also

- [Orchestration Methods Overview](../guides/orchestration.md)
- [Multimodal](../guides/multimodal.md) — when to enable multimodal samplers
- Source of truth: `src/llm4ad/planner/`
