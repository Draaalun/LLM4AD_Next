# DyCA Orchestrator

DyCA (Dynamic Clustering Adaptive) is the orchestrator to reach for when **different parts of your dataset benefit from different algorithms**. Instead of trying to evolve one solver that handles everything, DyCA clusters the dataset by behavior and evolves a specialist algorithm per cluster (plus a generalist as a fallback).

## When to use it

- Your dataset is heterogeneous (small vs. large TSP instances, easy vs. hard ML benchmarks).
- You can spare extra compute for clustering and per-cluster pools.
- You want to inspect specialist algorithms per regime, not just one global winner.

If your dataset is roughly homogeneous, [Island GA](island-ga.md) is simpler and equally effective.

## Configuration

```yaml
evolution:
  type: "dyca"
  max_generations: 30
  population_size: 8

  # Clustering
  n_clusters: 3
  clustering_method: "kmeans"          # or "agglomerative"
  recluster_interval: 5                # generations between recluster checks
  ari_threshold: 0.8                   # skip recluster if ARI ≥ threshold
  n_anchors: 5                         # anchors per cluster used as features

  # Pools
  generalist_pool_size: 10
  specialist_pool_size: 10
  complementary_pool_size: 10
  elite_archive_size: 5
  base_complementary_ratio: 0.2

  # SOS (signal-of-stagnation) escape
  sos_stagnation_threshold: 3

  offspring_per_generation: 5
  using_mode: false                    # freeze clustering once stable
```

All fields are validated by `DyCAConfig` (`src/llm4ad/config/evolution.py`). The default values come from that schema.

## How it works (briefly)

1. **Anchor evaluation** — at startup, run `n_anchors × n_clusters` algorithms on each instance to build a feature vector per instance.
2. **Cluster instances** — k-means (or agglomerative) over those vectors, producing `n_clusters` instance groups.
3. **Per-cluster evolution** — maintain three pools:
   - **Specialist pool**: top algorithms within a cluster.
   - **Generalist pool**: algorithms that perform well across all clusters.
   - **Complementary pool**: algorithms whose strengths complement existing pool members.
4. **Survival selection** — every cluster keeps its specialists; the generalist pool gets a slice of total budget controlled by `base_complementary_ratio`.
5. **Recluster check** — every `recluster_interval` generations, recluster and compute the Adjusted Rand Index (ARI) against the old clustering. If `ari ≥ ari_threshold`, the clustering is considered stable and skipped.
6. **SOS escape** — if `sos_stagnation_threshold` generations pass with no improvement, force a complementary push to escape local optima.

The orchestrator implementation lives at `src/llm4ad/orchestrator/dyca.py`; the planner-side cluster-aware samplers (`e1_sampler`, `e2_sampler`, `m1_sampler`, `m2_sampler`, `summary_sampler`, `complementary_cross_sampler`) live under `src/llm4ad/planner/sampler/dyca_samplers.py`.

## Operators

| Operator | Sampler | Purpose |
|---|---|---|
| `e1` | `e1_sampler` | Cluster-aware exploration: generate a new algorithm using cluster context |
| `e2` | `e2_sampler` | Cross-cluster exploration: combine signal across two clusters |
| `m1` | `m1_sampler` | Cluster-aware mutation of one parent |
| `m2` | `m2_sampler` | Aggressive mutation outside the cluster's current strategy |
| `summary` | `summary_sampler` | Summarize a cluster's elite algorithms; useful as a generalist seed |
| `complementary_cross` | `complementary_cross_sampler` | Cross specialist with complementary pool member |

These are all listed under `planner.samplers:` in YAML so you can disable individual operators by removing them.

## Worked example

The TSP example ships a DyCA config side-by-side with the Island GA and MEoH variants:

```bash
llm4ad run examples/applications/tsp_benchmark_python/tsp_dyca_config.yaml
```

It clusters the diverse dataset (small / clustered / large) and produces a specialist solver per cluster — visible in the run summary and in `runs/.../best/`. See the [TSP walkthrough](../examples/tsp.md#comparing-the-orchestrators).

## Tuning

Common knobs:

- **`n_clusters`** — start with the number of obvious regimes in your data; 2–4 is typical.
- **`n_anchors`** — more anchors give better feature vectors but cost more upfront LLM calls. 3–7 works.
- **`recluster_interval`** — small values (3–5) for fast-changing populations, large (10+) for stable ones.
- **`base_complementary_ratio`** — 0.1–0.3. Bigger means more compute on cross-cluster exploration.
- **`using_mode: true`** — once clustering looks stable, freeze it to focus all budget on specialist evolution.

## See also

- [Orchestration Methods Overview](orchestration.md) — when to pick DyCA over the alternatives
- [Planner API](../api/planner.md) — sampler chain reference
- [Configuration Guide](configuration.md) — full DyCA field documentation
- Source of truth: `src/llm4ad/orchestrator/dyca.py`
