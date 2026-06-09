# CLI Reference

LLM4AD ships a single CLI entrypoint, `llm4ad`, registered through the `llm4ad.frontend.cli:main` console script. This page documents every command, its arguments, and its exit codes.

Run `llm4ad --help` to print the same command list at any time.

## Top-level commands

| Command | Purpose |
|---|---|
| [`version`](#version) | Print the installed LLM4AD version |
| [`list`](#list) | List registered components (providers, planners, coders, evaluators, orchestrators) |
| [`init`](#init) | Copy a configuration template (minimal / standard / complete) into the current directory |
| [`run`](#run) | Run an algorithm-design pipeline from a YAML/JSON config |
| [`chat`](#chat) | Interactive consultant + builder; generates a complete LLM4AD application from natural language |
| [`advise`](#advise) | Analyze a single user-selected block (or every block) against an evolution goal |
| [`advise-init`](#advise-init) | Emit an `advise_config.yaml` template for the advisor |
| [`recommend`](#recommend) | Scan a repo and recommend evolve-block targets ranked by goal fit |
| [`evolve`](#evolve) | Subcommand group: inspect and clean `EVOLVE` markers in a task package |

> **Migration note.** The old `llm4ad build` and `llm4ad build-init` commands were merged into `llm4ad chat` in [#93](https://github.com/llm4ad/llm4ad/pull/93). All of the build flags (`--prompt`, `--code-path`, `--data-path`, `--non-interactive`, `--max-repair`) now live on `chat`. The placeholder `llm4ad config` was removed from the CLI; configuration display is best done by reading `~/.llm4ad/settings.yaml` and the task config directly.

Common conventions:

- All commands use Typer + Rich. Errors are printed to a Rich-styled `stderr` and the process exits with a non-zero code.
- Commands that talk to LLMs accept either a flag-driven setup (`--api-key`, `--model`, `--base-url`, `--provider-type`) or `--provider <name>` to pick a named provider from `~/.llm4ad/settings.yaml`.
- Commands that produce machine-readable output (`advise`, `recommend`, `evolve check`, `evolve clean`) emit JSON on stdout by default or under `--json`; use `--pretty` (advise/recommend) for a Rich panel.

## version

Print the installed LLM4AD version.

```bash
llm4ad version
```

Exit codes: `0` always.

## list

List components registered in each registry. Auto-discovers components in `llm4ad.infra.provider`, `llm4ad.planner`, `llm4ad.coder`, `llm4ad.evaluator`, and `llm4ad.orchestrator` before printing.

```bash
llm4ad list
llm4ad list --type provider
llm4ad list -t evaluator
```

| Option | Default | Description |
|---|---|---|
| `--type, -t` | _(all)_ | Filter to one of `provider`, `planner`, `coder`, `evaluator`, `orchestrator` |

Exit codes: `0` on success, `1` if `--type` is unknown.

## init

Copy one of the bundled configuration templates into the current directory so you can edit it before running `llm4ad run`.

```bash
llm4ad init                       # writes minimal.yaml
llm4ad init standard
llm4ad init complete -o my.yaml
```

| Argument / Option | Default | Description |
|---|---|---|
| `level` (positional) | `minimal` | One of `minimal`, `standard`, `complete` |
| `--output, -o` | `<level>.yaml` | Destination file name |

Behavior:

- If the destination exists, the user is prompted before overwriting.
- After writing, the next-step command is printed.

Exit codes: `0` on success, `1` for unknown level or missing template, `0` if the user declines to overwrite.

## run

Run an algorithm-design pipeline. Loads the YAML/JSON config, builds an `LLM4AD` instance, runs the pipeline asynchronously, and prints a summary including the best individual and (for multi-objective runs) the elitist archive.

```bash
llm4ad run config.yaml
llm4ad run config.yaml --output-dir ./runs
llm4ad run config.yaml -r ./runs/proj/run-2026-05-13/checkpoints/last.json
```

| Argument / Option | Default | Description |
|---|---|---|
| `config` (positional, required) | — | Path to the pipeline configuration |
| `--output-dir, -o` | _(from config)_ | Override `base_dir` from the config |
| `--resume, -r` | _(none)_ | Resume from the checkpoint at this path |

Output highlights:

- Per-pipeline summary printed before the run (`print_run_summary`).
- On completion, prints the best score (or per-objective bests) and any elitist-archive entries.
- Best worktree name is shown when the coder produced one.
- A `Best snapshot:` line points at the stable `best/` directory written at end of run (see [Architecture Data Flow § Run directory](../architecture/data-flow.md#run-directory-layout)).

Exit codes: `0` on completion (including non-improvement), `1` on any pipeline error (full traceback printed).

## chat

Interactive multi-turn consultant + builder. Walks the user through describing a problem, automatically generates the evaluator, algorithm template, and pipeline configuration, then optionally launches the run.

This command absorbed the old `llm4ad build` and `llm4ad build-init` (PR #93). Use the corresponding flags below to drive it non-interactively.

```bash
llm4ad chat                                                # full interactive flow
llm4ad chat --provider my-deepseek -o ./my_task/
llm4ad chat --resume <session-id>
llm4ad chat --list-sessions

# Skip the multi-turn conversation: provide the description directly.
llm4ad chat --prompt "evolve sorting algorithms that minimize comparisons"

# Adapt existing code instead of starting from scratch.
llm4ad chat --prompt "improve this heuristic" \
  --code-path ./solver/ --data-path ./data/

# Fully non-interactive (CI / batch use); requires --prompt.
llm4ad chat --prompt "evolve sorting" --non-interactive
```

| Option | Default | Description |
|---|---|---|
| `--provider, -p` | first provider in global settings | Provider name from `~/.llm4ad/settings.yaml` |
| `--resume, -r` | _(none)_ | Resume a previous session by ID or state-file path |
| `--output, -o` | `./` | Output directory for the generated application |
| `--list-sessions, -l` | `false` | List saved sessions and exit |
| `--max-repair` | `3` | Maximum auto-repair attempts during validation |
| `--prompt` | _(none)_ | Provide the full problem description directly (skips Phase 1 conversation) |
| `--non-interactive` | `false` | Skip all interactive phases (requires `--prompt`) |
| `--code-path` | _(none)_ | Path to existing algorithm code to adapt |
| `--data-path` | _(none)_ | Path to dataset directory or files |

Behavior:

- Requires `~/.llm4ad/settings.yaml` to define at least one provider; otherwise exits with guidance.
- After the user completes the consultation, optionally launches the generated pipeline immediately.
- Generated files land at `{output}/{project_name}/`; see [Auto Builder](auto-builder.md) for the full directory shape and the validation pipeline.

Exit codes: `0` on success, `130` on Ctrl-C / EOF, `1` on provider-resolution or run errors.

## advise

Analyze a user-selected EVOLVE block (or every block in the repo) against an evolution goal and return structured advice (summary, feasibility, significance, concerns, suggestions, rationale).

The command **always** returns the same envelope `{goal, repo_path, lang, count, results, errors}` so a frontend never needs to discriminate single-block vs multi-block output. Default output is JSON on stdout for backend consumption; use `--pretty` for Rich panels (one per result).

```bash
llm4ad advise -g "minimize comparisons" -r ./solver --file algo.py --range 42:87
llm4ad advise -g "reduce tour length" -r ./solver           # auto-locates the single EVOLVE block
llm4ad advise -g "minimize sort comparisons" -r ./solver --block-id 'algo/sort.py#12-162'
llm4ad advise -g "tune all heuristics" -r ./solver --all --max-concurrency 8
llm4ad advise --config advise_config.yaml
llm4ad advise -g "improve policy" --code "$(cat snippet.py)"
```

| Option | Default | Description |
|---|---|---|
| `--goal, -g` | _(required unless `--config`)_ | Evolution goal to analyze against |
| `--config, -f` | _(none)_ | Path to an advisor config YAML (alternative to flags) |
| `--repo, -r` | _(none)_ | Repository path containing the block(s) |
| `--file` | _(none)_ | File path (relative to `--repo` or absolute) |
| `--range` | _(none)_ | 1-based inclusive line range, format `START:END` (e.g. `42:87`) |
| `--code` | _(none)_ | Raw snippet to analyze instead of a repo path |
| `--block-id` | _(none)_ | Stable id from `llm4ad evolve check` (e.g. `algo/sort.py#12-162`) to select one block in `--repo` |
| `--all` | `false` | Analyze every well-formed EVOLVE block in `--repo` (concurrent). Files with marker issues are skipped — run `evolve check` first |
| `--max-concurrency` | `5` | Max parallel LLM calls when `--all` is set |
| `--api-key` | env `LLM4AD_ADVISE_API_KEY` | Advisor LLM API key |
| `--model` | `gpt-4o` | Advisor LLM model name |
| `--base-url` | _(provider default)_ | Advisor LLM base URL |
| `--provider-type` | `openai_compatible` | One of `openai`, `anthropic`, `openai_compatible` |
| `--provider, -p` | _(none)_ | Use a named provider from `~/.llm4ad/settings.yaml` |
| `--lang` | `en` | Language for the LLM's free-text answers: `en` or `zh`. Surfaced as `lang` on the envelope. |
| `--pretty` | `false` | Render Rich panel(s) instead of JSON |

**Mutual exclusivity:** `--all` is incompatible with `--code`, `--file`, `--range`, `--block-id`. `--block-id` is incompatible with `--file`, `--range`, `--code`. `--code` is incompatible with `--repo`, `--file`, `--range`, `--block-id`, `--all`.

**Resolution order for single-block path:** `--code` → explicit `--repo --file --range` → `--repo --block-id` → auto-locate the unique `EVOLVE` block in `--repo`.

**Output envelope:**

```json
{
  "goal": "...",
  "repo_path": "/abs/path",
  "lang": "en",
  "count": 1,
  "results": [ /* one BlockAdvice per analyzed block */ ],
  "errors":  [ /* per-block failures, only set when --all */ ]
}
```

`--all` populates `results` for every successful block and `errors` for any block whose LLM call failed (the run continues regardless). Single-block paths always have `count==1` and `errors==[]`.

Exit codes: `0` on success, `1` on `AdvisorError`, malformed `--range`, missing `--goal`/`--config`, unknown `--lang`, mutex violations, or any other failure.

## advise-init

Emit an `advise_config.yaml` template for `llm4ad advise --config <file>`.

```bash
llm4ad advise-init
llm4ad advise-init -o my_advise.yaml
llm4ad advise-init -g "minimize sort comparisons"
```

| Option | Default | Description |
|---|---|---|
| `--output, -o` | `advise_config.yaml` | Destination path |
| `--goal, -g` | `""` | Pre-fill the goal field |

Exit codes: `0` on success.

## recommend

Scan a repository against a goal and recommend evolve-block targets, returned in three tiers: a **core** block (minimal recommendation), optional **expanded** variants of the core block, and optional **alternatives** elsewhere. LLM4AD currently evolves one block per run — these tiers are alternative *choices*, not co-evolution targets.

```bash
llm4ad recommend -g "reduce TSP tour length" -r ./solver
llm4ad recommend -g "improve policy reward" -r ./lander --pretty
llm4ad recommend -g "..." -r ./repo --max-concurrency 8 --include-raw
```

| Option | Default | Description |
|---|---|---|
| `--goal, -g` | _(required)_ | Evolution goal |
| `--repo, -r` | _(required)_ | Repository to scan |
| `--api-key` | env `LLM4AD_ADVISE_API_KEY` | Recommender LLM API key |
| `--model` | `gpt-4o` | Recommender LLM model name |
| `--base-url` | _(provider default)_ | Recommender LLM base URL |
| `--provider-type` | `openai_compatible` | One of `openai`, `anthropic`, `openai_compatible` |
| `--provider, -p` | _(none)_ | Use a named provider from `~/.llm4ad/settings.yaml` |
| `--max-concurrency` | `5` | Max parallel advice calls during enrichment |
| `--include-raw` | `false` | Include raw discovery-LLM text in the output (debug) |
| `--lang` | `en` | Language for the LLM's free-text answers: `en` or `zh`. Threaded through both the discovery call and every per-block advice call; surfaced as `lang` in the output JSON. |
| `--pretty` | `false` | Render Rich panels instead of JSON |

Output:

- JSON mode (default): full `RepoRecommendations.to_dict()` with `core`, `expanded`, `alternatives`, `dropped_candidates`, `unreadable_files`, `lang`.
- `--pretty`: stack of Rich panels with location, rationale, advice (feasibility, significance, concerns, suggestions, rationale).

Exit codes: `0` on success, `1` on missing `--goal`/`--repo`, unknown `--lang`, `AdvisorError`, or any other failure.

## evolve

Subcommand group for inspecting and cleaning `EVOLVE` markers in a task package.

A "marker line" is a comment line whose content (after stripping the comment leader `#`, `//`, `/*`, or `<!--`) starts with `EVOLVE_START` or `EVOLVE_END`. Prose that mentions `EVOLVE_START` inside a docstring or string literal is **not** a marker.

The Python API behind these commands is exported from `llm4ad.infra.repo_analyzer`:

```python
from llm4ad.infra.repo_analyzer import inspect_path, clean_path

inspect_path("path/to/pkg").to_dict()
clean_path("path/to/pkg", apply=True).to_dict()
```

### evolve check

Inspect markers in a task package: count well-formed blocks, detect nested or unbalanced markers, and flag the **active** block (the one planners currently feed to the coder as `evolvable_blocks[0]`).

```bash
llm4ad evolve check                                    # inspects current directory
llm4ad evolve check ./examples/applications/sorting_benchmark_python
llm4ad evolve check ./pkg --json                        # machine-readable
llm4ad evolve check ./pkg -i "*.py" -e "tests/**"
```

| Argument / Option | Default | Description |
|---|---|---|
| `path` (positional) | `.` | Task package directory |
| `--include, -i` | _(detector defaults)_ | Glob to include (repeatable) |
| `--exclude, -e` | _(detector defaults)_ | Glob to exclude (repeatable) |
| `--json` | `false` | Emit `InspectResult.to_dict()` on stdout |

Human-readable output (no `--json`) prints three Rich tables:

1. **Inspection summary** — root, files scanned, files with blocks, total blocks, total issues, active block id.
2. **Discovered blocks** — the `Active` column shows `*` for the block that will be evolved.
3. **Issues** — one row per `nested`, `unbalanced_start`, `unbalanced_end`, or `unreadable` issue.

JSON mode emits the same data:

```json
{
  "ok": true,
  "root": "/abs/path",
  "summary": {"files_scanned": 4, "files_with_blocks": 1, "blocks": 1,
              "issues": 0, "active_block_id": "policy/choose_action.py#27-87"},
  "files": [
    {"path": "policy/choose_action.py", "language": "python",
     "blocks": [{"line_start": 27, "line_end": 87, "comment_style": "#",
                 "block_name": "", "block_id": "policy/choose_action.py#27-87",
                 "active": true}],
     "issues": []}
  ]
}
```

`block_id` is `f"{rel_posix_path}#{line_start}-{line_end}"` and is stable across runs.

Exit codes: `0` if `ok=true` (no issues), `1` if any issue is found or the path doesn't exist.

### evolve clean

Remove every `EVOLVE_START` / `EVOLVE_END` marker line from files in a task package, preserving the block bodies and surrounding context. Defaults to **dry-run**: no files are written, but the report shows which lines would be removed.

```bash
llm4ad evolve clean ./pkg                  # dry-run (no writes)
llm4ad evolve clean ./pkg --apply          # actually rewrite files
llm4ad evolve clean ./pkg --apply --json
```

| Argument / Option | Default | Description |
|---|---|---|
| `path` (positional) | `.` | Task package directory |
| `--apply` | `false` | Rewrite files in place. Without it, dry-run only. |
| `--include, -i` | _(detector defaults)_ | Glob to include (repeatable) |
| `--exclude, -e` | _(detector defaults)_ | Glob to exclude (repeatable) |
| `--json` | `false` | Emit `CleanResult.to_dict()` on stdout |

Human-readable output prints a summary table (mode, files changed, lines removed, errors) and a per-file table with the line numbers that were (or would be) removed and a `Written` column. JSON mode emits the same data:

```json
{
  "ok": true,
  "applied": true,
  "root": "/abs/path",
  "summary": {"files_changed": 1, "lines_removed": 2, "errors": 0},
  "files": [
    {"path": "algo/sort.py", "removed_lines": [2, 4], "written": true}
  ]
}
```

Notes:

- File walking respects the same default include / exclude patterns as `EvolveDetector` so the cleaner sees exactly the files the analyzer scans during evolution.
- Errors during read or write are recorded per file (`error` field) and flip `ok` to `false`, but the run continues for the remaining files.

Exit codes: `0` on success, `1` if any file errored or the path doesn't exist.

## See also

- [Quick Start](quickstart.md) — your first end-to-end run.
- [Configuration](configuration.md) — YAML schema reference.
- [Auto Builder](auto-builder.md) — what `llm4ad chat` does end-to-end.
- [Advisor](advisor.md), [Recommender](recommender.md) — deeper context for `advise` / `recommend`.
