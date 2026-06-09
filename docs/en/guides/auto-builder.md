# Auto Builder (`llm4ad chat`)

The auto builder generates a complete, runnable LLM4AD application from a natural-language description. The CLI command is `llm4ad chat` (`llm4ad build` and `llm4ad build-init` were merged into `chat` in [#93](https://github.com/llm4ad/llm4ad/pull/93)). The Python builder API (`build_task_sync`, `build_from_config`, `build_from_config_sync`) is stable and is what backend integrations call.

This page covers the workflow, the auto-repair behavior, and how to use it from the CLI and from Python.

## What it produces

Given a description like:

> "Evolve sorting algorithms that minimize comparisons and execution time"

the builder produces a complete application directory:

```
{task_dir}/
├── config.yaml                    # pipeline configuration
├── {project_name}_evaluator.py    # custom evaluator with metrics
├── {algorithm_dir}/{algorithm}.py # algorithm template with EVOLVE markers
├── debug_run.py                   # quick local testing script
├── test_evaluator.py              # end-to-end evaluator validation
├── data/sample/                   # sample test data
└── blueprint_meta.json            # build metadata
```

After the build finishes you can immediately run `llm4ad run {task_dir}/config.yaml`.

## Four-stage pipeline

1. **Analyze** (`TaskAnalyzer`) — extract task structure from natural language: function signature, metrics, input/output formats, multimodal hint.
2. **Create** (`TaskCreator`) — generate evaluator code, algorithm template with EVOLVE markers, config YAML, debug runner, test_evaluator, sample data.
3. **Validate** (`TaskValidator`) — run static checks (syntax, config structure, EVOLVE markers, multimodal imports) and runtime checks (imports, algorithm trial, debug_run, test_evaluator). On failure, route the error to the right artifact and ask the LLM to repair just that artifact.
4. **Write** (`TaskWriter`) — write the validated blueprint to disk.

### Validation stages

| Stage | Check | Repair target |
|---|---|---|
| 1 | Python syntax (evaluator, algorithm, debug_run, test_evaluator) | Targeted artifact |
| 2 | Config YAML structure | Full regeneration |
| 3 | EVOLVE markers present | Algorithm code |
| 4 | Multimodal imports (if enabled) | Evaluator code |
| 5 | Evaluator module imports, class exists | Evaluator code |
| 6 | Algorithm runs with sample data | Algorithm or dataset |
| 7 | `debug_run.py` executes | debug_run code |
| 8 | `test_evaluator.py` passes | Evaluator + test_evaluator |

The validator is **smart about routing**: a JSON parse error in the algorithm stage points at the dataset rather than the algorithm; repeated identical errors escalate to a full regeneration. After `max_repair_attempts` failed attempts (default 3), the build fails with `BuildError`.

## CLI usage

```bash
# Conversational build (full multi-turn)
llm4ad chat

# Skip Phase 1 conversation: provide the description directly
llm4ad chat --prompt "evolve sorting algorithms that minimize comparisons"

# Fully non-interactive (CI / batch use)
llm4ad chat --prompt "evolve sorting" --non-interactive

# Adapt existing code instead of starting fresh
llm4ad chat --prompt "improve this heuristic" \
  --code-path ./solver/ --data-path ./data/

# Use a named provider from ~/.llm4ad/settings.yaml
llm4ad chat --provider my-deepseek

# Resume a saved session
llm4ad chat --resume <session-id>
llm4ad chat --list-sessions
```

The full flag list is in the [CLI Reference](cli.md#chat).

After the build, `llm4ad chat` will offer to run the generated pipeline immediately.

## Python API

```python
from llm4ad.builder import build_from_config_sync, build_from_config

# Synchronous (scripts / notebooks)
task_dir = build_from_config_sync("build_config.yaml")

# Async (FastAPI / web backends)
task_dir = await build_from_config("build_config.yaml")

# Then run the generated pipeline
from llm4ad import LLM4AD
llm4ad = LLM4AD(f"{task_dir}/config.yaml")
result = await llm4ad.run()
```

For multi-user web platforms, see [Frontend Integration](../web-ui/frontend-integration.md) — it covers async/queued patterns, polling, security, and a complete FastAPI example.

## `build_config.yaml` format

When you don't want to pass everything via CLI flags, use a config file:

```yaml
builder:
  type: "openai_compatible"
  base_url: "${LLM4AD_BUILD_BASE_URL}"
  api_key: "${LLM4AD_BUILD_API_KEY}"
  model: "gpt-4o"
  max_repair_attempts: 3

task:
  description: |
    Evolve sorting algorithms that minimize comparisons and execution time.
    Input: list of integers.
    Output: sorted list.
  output_dir: "./output/"
  project_name: "my_task"
  multimodal: false
  visualization_hint: ""
```

Then:

```bash
llm4ad chat --prompt "$(cat task_description.md)" --output ./my_tasks/
# or, programmatically:
build_from_config_sync("build_config.yaml")
```

`${VAR_NAME}` placeholders are expanded at load time against the process environment.

## Generated `test_evaluator.py`

Unlike a syntax-only check, the builder generates a complete runtime test:

- imports the evaluator class,
- loads sample data,
- calls `evaluate()` with a real `EvalContext`,
- verifies expected metrics are present,
- prints `[PASS]` or `[FAIL]` and exits with the appropriate code.

This is what guarantees the evaluator actually works at validation time, not just that it parses.

## Multimodal builds

When `task.multimodal: true`:

- The evaluator scaffold returns visualization images via `BehaviorData`.
- `behavior_storage` parameter handling is wired up.
- Renderers for deferred visualization are stubbed.
- `test_evaluator.py` passes `behavior_storage="rendered"` to `EvalContext` to exercise the multimodal path.

See [Multimodal](multimodal.md) for what happens when the evolution actually runs.

## Best practices

### For users

1. **Be specific in descriptions** — input/output formats, evaluation criteria, constraints. Vague descriptions lead to brittle scaffolding.
2. **Use environment variables** for API keys (`LLM4AD_BUILD_API_KEY`, etc.) instead of inlining them in the config.
3. **Test locally first** — run `python {task_dir}/debug_run.py` before kicking off real evolution.
4. **Review the generated code** — the builder is good but not perfect; eyeball the evaluator logic.

### For platform integrators

1. **Use the config-based workflow** — generate `build_config.yaml` from form input on the backend, then call `build_from_config()`.
2. **Isolate user builds** — use per-user output dirs (`/data/builds/{user_id}/{task_id}/`).
3. **Run async** — `build_from_config()` (async) is the right choice in FastAPI; `_sync` blocks for minutes.
4. **Monitor repair attempts** — log validation errors so you can spot recurring failure modes.
5. **Set hard timeouts** — builds typically take 2–5 minutes; cap at 10 minutes.

## Limitations

- **Quality depends on the builder LLM** — `gpt-4o` or similar is recommended.
- **Complex evaluation logic** may need manual refinement after the build.
- **Domain-specific knowledge** is best-effort — well-known algorithmic tasks (sorting, TSP, ML hyperparams) work better than esoteric ones.
- **After 3 failed repairs**, manual intervention is required (the build returns `BuildError`).

## Examples

`examples/auto_applications/` ships:

- `from_code/` — adapt existing code (TSP, CVRP)
- `from_description/` — start from a natural-language brief (bipedal_walker, CVRP)
- `build_config.yaml` templates and the generated outputs

These are good starting points if you want to see the full input → output of the builder.

## See also

- [CLI Reference § chat](cli.md#chat)
- [Frontend Integration](../web-ui/frontend-integration.md) — embedding into a multi-user platform
- [Configuration Guide](configuration.md) — the schema the builder writes
