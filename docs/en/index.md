# LLM4AD Documentation

Welcome to **LLM4AD** — an automated algorithm design platform powered by large language models and evolutionary computation. This site is the canonical reference for the open-source repository as well as the content source for the in-app User Manual served by the Web UI.

## What LLM4AD is

LLM4AD treats the LLM as a **proposer** and evolutionary computation as the **evaluator and selector**. The two cooperate iteratively to search for better algorithms. The design goals are:

- Let the LLM only edit code regions you marked with `EVOLVE_START` / `EVOLVE_END` in your existing repository.
- Evaluate many candidates in parallel via isolated git worktrees, with no main-branch pollution.
- Decouple evolution strategy (Island GA, DyCA, MEoH), evaluation (Python / executable / benchmark / LLM-judge), and provider (OpenAI-compatible, Anthropic, Mock) into pluggable, registry-driven components.
- Drive the whole pipeline from a single YAML config; CLI, Python API, and Web UI all share the same runtime.

## Highlights

- **Multiple orchestration strategies**: [Island GA](guides/island-ga.md) for classic parallelism; [DyCA](guides/dyca.md) for instance-clustering with specialist algorithms; [MEoH](guides/meoh.md) for true multi-objective Pareto fronts. See [Orchestration Methods](guides/orchestration.md).
- **A flexible evaluator layer**: mix-and-match `PythonEvaluator` / `BenchmarkEvaluator`, `ExecutableEvaluator`, `LLMJudgeEvaluator`, with multi-instance parallelism and multi-objective aggregation.
- **Multimodal evolution**: behavior images / trajectories returned by an evaluator flow straight into prompts so the LLM can "see" what an algorithm does ([Multimodal](guides/multimodal.md)).
- **Embeddings and trajectory visualization**: the `local` dual-endpoint mode lets text and code use different embeddings; 3D HTML trajectory plots make the evolution process visible ([Embeddings & Trajectory](guides/embeddings.md)).
- **CLI + Web UI**: CLI (`llm4ad run` / `chat` / `advise` / `recommend` / `evolve`) plus a Docker-shipped frontend/backend Web UI ([Web UI Overview](web-ui/overview.md)).
- **Auto Builder**: spin up an evaluator, algorithm template, and YAML config from a natural-language description with `llm4ad chat` ([Auto Builder](guides/auto-builder.md)).

## Quick start

```bash
git clone https://github.com/Optima-CityU/LLM4AD_Next.git
cd llm4ad
uv sync

export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

llm4ad run examples/applications/sorting_benchmark_python/config.yaml
```

The full walkthrough lives in [Quick Start](guides/quickstart.md).

## Path map

| If you want to | Start here |
|---|---|
| Run LLM4AD for the first time | [Installation](guides/installation.md) → [Quick Start](guides/quickstart.md) |
| Understand every YAML field | [Configuration Guide](guides/configuration.md) |
| Plug in your own project | [Evaluators Guide](guides/evaluators.md) + [Auto Builder](guides/auto-builder.md) |
| Pick an orchestrator | [Orchestration Methods Overview](guides/orchestration.md) |
| Connect a new LLM service | [Providers Guide](guides/providers.md) |
| Tune timing and concurrency | [Timing & Metrics](guides/timing-metrics.md) + [Advanced Configuration](guides/advanced.md) |
| Run the Web UI / self-deploy | [Web UI Overview](web-ui/overview.md) + [Frontend Integration](web-ui/frontend-integration.md) |
| Extend the framework | [Architecture Overview](architecture/overview.md) → [API Reference](api/index.md) |
| Contribute | [Contribution Guidelines](contributing/guidelines.md) → [Development Setup](contributing/development.md) |

## Project layout

```
LLM4AD/
├── src/llm4ad/             # Python library
│   ├── config/              # Pydantic schemas and global settings
│   ├── infra/               # providers / state / timing / repo analyzer / worktrees
│   ├── planner/             # planners and samplers (proposal generation)
│   ├── coder/               # code-generation backends (custom / claude_code / opencode)
│   ├── evaluator/           # evaluator base classes and dispatcher
│   ├── orchestrator/        # evolution orchestrators (island_ga / dyca / meoh)
│   ├── consultant/          # llm4ad chat backend
│   ├── advisor/             # llm4ad advise / recommend backend
│   ├── frontend/cli.py      # CLI entry point
│   └── utils/               # registry and cross-cutting helpers
├── src/backend/            # FastAPI web backend
├── src/frontend/           # React + Vite frontend
├── examples/applications/  # 17 runnable example projects
├── docs/                   # Bilingual documentation (this site)
└── pyproject.toml
```

## What's new

Recent highlights (full list in [Changelog](changelog.md)):

- **`llm4ad chat` and `llm4ad build` are merged** into a unified three-phase command.
- **Stable `best/` snapshot** is exported at end of every run (with `best/pareto/<idx>/` for multi-objective).
- **MEoH orchestrator** delivers a real multi-objective Pareto front.
- **Embedding `local` mode** routes text and code to different endpoints.
- **`llm4ad evolve check / clean`** brings EVOLVE-marker inspection and cleanup to the CLI.

## License

This project is released under the MIT license — see [LICENSE](license.md).

## Support

- 📖 [Documentation site](https://llm4ad.readthedocs.io)
- 💬 [GitHub Discussions](https://github.com/Optima-CityU/LLM4AD_Next/discussions)
- 🐛 [Issue Tracker](https://github.com/Optima-CityU/LLM4AD_Next/issues)
