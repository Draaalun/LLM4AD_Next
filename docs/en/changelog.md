# Changelog

All notable changes to LLM4AD are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `ref:`).

LLM4AD is currently in alpha (`0.1.x`) and has not cut tagged releases yet. Sections below group changes by the calendar month in which they merged to `main`. Once a versioned release is cut, ranges will be backfilled with version numbers.

## [Unreleased] — May 2026

### Web UI
- **feat**: file create/rename APIs, confirmation dialogs, and UX improvements ([#106](https://github.com/llm4ad/llm4ad/pull/106))
- **fix**: rapid evolutionary analysis now supports multiple displays ([#104](https://github.com/llm4ad/llm4ad/pull/104))
- **fix**: nginx now refreshes DNS for upstream services ([#107](https://github.com/llm4ad/llm4ad/pull/107))
- **fix**: build stage moved to common block to prevent build errors ([#103](https://github.com/llm4ad/llm4ad/pull/103))
- **fix**: AI recommendation no longer yields empty results ([#105](https://github.com/llm4ad/llm4ad/pull/105))

### CLI & tooling
- **feat (breaking)**: `llm4ad chat` and `llm4ad build` are merged into a single three-phase command (consult → build → run) ([#93](https://github.com/llm4ad/llm4ad/pull/93)). Old invocations of `llm4ad build` and `llm4ad build-init` should migrate to `llm4ad chat` with the corresponding flags. See [Auto Builder](guides/auto-builder.md).
- **feat**: `llm4ad advise` gains `--all` and `--block-id`, with a unified result envelope so the frontend can treat single-block and batch outputs the same way ([#94](https://github.com/llm4ad/llm4ad/pull/94)).
- **feat**: `llm4ad evolve check` and `llm4ad evolve clean` for inspecting and removing EVOLVE markers in a task package ([#89](https://github.com/llm4ad/llm4ad/pull/89)).
- **feat**: `--lang` option on `llm4ad recommend` and `llm4ad advise` to localize the LLM's free-text answers (`en` or `zh`) ([#92](https://github.com/llm4ad/llm4ad/pull/92)).

### Providers & embeddings
- **feat**: DeepSeek thinking-mode `reasoning_content` is preserved across multi-turn chat ([#98](https://github.com/llm4ad/llm4ad/pull/98)).
- **feat (embeddings)**: per-task routing via the new `local` provider mode lets text and code endpoints differ ([#90](https://github.com/llm4ad/llm4ad/pull/90)). See [Embeddings & Trajectory](guides/embeddings.md).
- **feat**: batched embedding requests and a deterministic mock provider ([#88](https://github.com/llm4ad/llm4ad/pull/88)).

### Orchestration & runs
- **feat**: best individual is exported to a stable `best/` directory at run end (with `best/pareto/<idx>/` per archive entry for multi-objective runs) ([#95](https://github.com/llm4ad/llm4ad/pull/95)).
- **fix**: resolve "invalid reference: HEAD" error during worktree creation ([#99](https://github.com/llm4ad/llm4ad/pull/99)).
- **fix**: lunarlander evaluators now use `episode_reward` as score ([#96](https://github.com/llm4ad/llm4ad/pull/96)).
- **fix/perf**: bilevel search efficiency for symbolic regression improved ([#97](https://github.com/llm4ad/llm4ad/pull/97)).

## April 2026

### CLI & tooling
- **feat**: `llm4ad recommend` (evolve-block recommender) — scans a repo and suggests core / expanded / alternative blocks for a goal ([#74](https://github.com/llm4ad/llm4ad/pull/74)).
- **feat**: `llm4ad advise` (evolve-block advisor) — analyzes a single block against an evolution goal ([#73](https://github.com/llm4ad/llm4ad/pull/73)).
- **feat**: automated LLM4AD application builder with runtime validation ([#46](https://github.com/llm4ad/llm4ad/pull/46)) — later subsumed into `llm4ad chat` ([#93](https://github.com/llm4ad/llm4ad/pull/93)).
- **feat**: smart EVOLVE block analysis and driver extraction ([#52](https://github.com/llm4ad/llm4ad/pull/52)).
- **ref**: simplify EvolveDetector ([#54](https://github.com/llm4ad/llm4ad/pull/54)).

### Web UI
- **feat**: initial frontend and backend code lands ([#58](https://github.com/llm4ad/llm4ad/pull/58)).
- **feat**: research page and Insights report generation ([#68](https://github.com/llm4ad/llm4ad/pull/68)).
- **feat**: evolution block selection, advisor service, and trajectory visualization ([#84](https://github.com/llm4ad/llm4ad/pull/84)).
- **feat**: 3D HTML trajectory visualization with algorithm embedding pipeline ([#78](https://github.com/llm4ad/llm4ad/pull/78), [#79](https://github.com/llm4ad/llm4ad/pull/79)).
- **feat**: dark mode + custom retry logic + async embedding ([#80](https://github.com/llm4ad/llm4ad/pull/80)).

### Orchestration
- **feat**: MEoH (multi-objective evolution of heuristics) lands as a new orchestrator ([#65](https://github.com/llm4ad/llm4ad/pull/65)).
- **feat**: DyCA 2.0 — refined clustering and multi-pool resource allocation ([#37](https://github.com/llm4ad/llm4ad/pull/37)).
- **feat**: concurrency control for evaluation and LLM pipelines ([#35](https://github.com/llm4ad/llm4ad/pull/35)).

### Evaluators & examples
- **feat**: `LLMJudgeEvaluator` base class + `life_planning` example ([#32](https://github.com/llm4ad/llm4ad/pull/32), [#44](https://github.com/llm4ad/llm4ad/pull/44), [#49](https://github.com/llm4ad/llm4ad/pull/49), [#55](https://github.com/llm4ad/llm4ad/pull/55)).
- **add**: ICM-MCM 2024D and 2025D applications ([#48](https://github.com/llm4ad/llm4ad/pull/48), [#51](https://github.com/llm4ad/llm4ad/pull/51)).
- **add**: ML benchmark example ([#36](https://github.com/llm4ad/llm4ad/pull/36)).
- **feat**: bilevel search for symbolic regression tasks ([#33](https://github.com/llm4ad/llm4ad/pull/33)).
- **ref**: standardize all example `config.yaml` to match `config.complete.yaml` ([#70](https://github.com/llm4ad/llm4ad/pull/70)).

### Framework
- **feat**: split config schema, memory extraction, human-readable timing, per-generation token logging ([#31](https://github.com/llm4ad/llm4ad/pull/31)).
- **feat**: refactor evaluator module with discriminated config, build system, and `EvalContext` rename ([#20](https://github.com/llm4ad/llm4ad/pull/20)).
- **fix**: add missing `behavior_storage` field to `EvalContext` ([#43](https://github.com/llm4ad/llm4ad/pull/43)).

## March 2026

Foundational work prior to the April rollout — initial multi-objective MEoH, DyCA, multimodal evolution (MLES), interactive consultant, mock provider, and the rest of the platform's first iteration. Highlights:

- **feat**: interactive consultant module, global settings, provider streaming ([#22](https://github.com/llm4ad/llm4ad/pull/22)).
- **feat**: DyCA orchestrator for multi-distribution evolution ([#18](https://github.com/llm4ad/llm4ad/pull/18)).
- **feat**: multimodal LLM-based evolution strategy (MLES) — initial implementation.
- **feat**: mock LLM provider + `tsp_benchmark_python_mock` example.
- **feat**: opencode coder ([#12](https://github.com/llm4ad/llm4ad/pull/12)).
- **feat**: configurable sampler selection with dynamic weight adjustment ([#10](https://github.com/llm4ad/llm4ad/pull/10)).
- **feat**: TSP example, sorting benchmark converted to Python ([#9](https://github.com/llm4ad/llm4ad/pull/9)).
- **feat**: initial implementation, including custom naive coder, Island GA orchestrator, run summary, and logging ([#2](https://github.com/llm4ad/llm4ad/pull/2)–[#7](https://github.com/llm4ad/llm4ad/pull/7)).

## See also

- [Contribution Guidelines](contributing/guidelines.md) — commit format that drives this changelog
- [Latest commits on GitHub](https://github.com/llm4ad/llm4ad/commits/main) — the full source of truth
