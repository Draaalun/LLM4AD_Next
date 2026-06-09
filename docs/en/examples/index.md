# Examples Gallery

LLM4AD ships seventeen runnable example projects under `examples/applications/`. Each has its own `config.yaml`, evaluator, and algorithm template — pick one close to your problem, copy it, and adapt.

The walkthroughs below dive into the most representative ones. The full table at the bottom lists every shipped example with a link to its source.

## Featured walkthroughs

| Example | Domain | Orchestrator | Highlights |
|---|---|---|---|
| [Sorting Benchmark](sorting.md) | Algorithm engineering | Island GA | Single-objective, fastest path to a working run |
| [TSP Benchmark](tsp.md) | Combinatorial optimization | Island GA / DyCA / MEoH | Three orchestrators side-by-side on the same task |
| [LunarLander (RL)](lunarlander.md) | Reinforcement learning | Island GA / DyCA | Policy search in OpenAI Gym, with multimodal variant |
| [Symbolic Regression](symbolic-regression.md) | Scientific discovery | Island GA | Bilevel evaluation with predefined constants |
| [ML Hyperparameter Search](ml-hyperpara.md) | AutoML | Island GA | Tune routine evolution under a time budget |

## Full example index

Source root: [`examples/applications/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications).

| Example | Path | Multimodal | Notes |
|---|---|---|---|
| sorting_benchmark | `examples/applications/sorting_benchmark/` | — | Executable evaluator (C++ build) |
| sorting_benchmark_python | `examples/applications/sorting_benchmark_python/` | — | Pure-Python; featured in [Sorting](sorting.md) |
| tsp_benchmark_python | `examples/applications/tsp_benchmark_python/` | — | Featured in [TSP](tsp.md); ships Island GA, DyCA, and MEoH configs |
| tsp_benchmark_python_mock | `examples/applications/tsp_benchmark_python_mock/` | — | Same task with `MockProvider` for tests/CI |
| tsp_benchmark_python_multimodal | `examples/applications/tsp_benchmark_python_multimodal/` | ✓ | Tour visualizations injected into prompts |
| lunarlander_python | `examples/applications/lunarlander_python/` | — | Featured in [LunarLander](lunarlander.md); `lunarlander_dyca_config.yaml` included |
| lunarlander_python_multimodal | `examples/applications/lunarlander_python_multimodal/` | ✓ | Trajectory frames inform mutations |
| ml_feature_benchmark | `examples/applications/ml_feature_benchmark/` | — | Feature-selection task |
| ml_hyperpara_benchmark | `examples/applications/ml_hyperpara_benchmark/` | — | Featured in [ML Hyperparameter Search](ml-hyperpara.md) |
| symbolic_regression_bilevel_predefined_constant | `examples/applications/symbolic_regression_bilevel_predefined_constant/` | — | Featured in [Symbolic Regression](symbolic-regression.md) |
| relationship_prediction | `examples/applications/relationship_prediction/` | — | Multi-instance LLM-judge evaluator |
| life_planning | `examples/applications/life_planning/` | — | LLM-judge evaluator on long-form plans |
| MCM_ICM_problem_2024_D | `examples/applications/MCM_ICM_problem_2024_D/` | — | Competition-style modeling problem |
| task_template_python | `examples/applications/task_template_python/` | — | Minimal scaffold to copy when starting fresh |
| task_template_python_multimodal | `examples/applications/task_template_python_multimodal/` | ✓ | Multimodal scaffold |

Auto-generated examples (produced by `llm4ad chat`, kept under [`examples/auto_applications/`](https://github.com/llm4ad/llm4ad/tree/main/examples/auto_applications)) demonstrate the [Auto Builder](../guides/auto-builder.md) flow end-to-end.

## How to run any example

```bash
cd LLM4AD
uv sync
export LLM_API_KEY="sk-..."
export LLM_BASE_URL="https://api.openai.com/v1"   # optional
export LLM_MODEL="gpt-4o-mini"

llm4ad run examples/applications/sorting_benchmark_python/config.yaml
```

The run directory lands at `./runs/<project_name>/<run_id>/` and the CLI prints the `best/` snapshot path on completion.

## See also

- [Quick Start](../guides/quickstart.md) — the smallest end-to-end run
- [Configuration Guide](../guides/configuration.md) — every YAML key explained
