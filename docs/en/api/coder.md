# Coder API

`llm4ad.coder` materializes a planner's proposed algorithm into runnable code. A coder edits files inside a worktree, calls an underlying LLM backend, and hands the result to the evaluator.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `BaseCoder` | Abstract coder; subclass and call `register_coder("name")` | `src/llm4ad/coder/base.py` |
| `ClaudeCodeCoder` | Agent-style editing via the Anthropic Claude Code CLI | `src/llm4ad/coder/claude_code.py` |
| `OpenCodeCoder` | Agent-style editing via the OpenCode CLI | `src/llm4ad/coder/opencode.py` |
| `CustomCoder` | Naive LLM coder; edits EVOLVE blocks directly via unified diff | `src/llm4ad/coder/custom_naive_coder.py` |
| `GenerateResult`, `GenerateStatus` | Return envelope for coder calls (`SUCCESS`, `FAILED`, `TIMEOUT`, `PARTIAL`) | `src/llm4ad/coder/base.py` |

## Worktree integration

Every coder call runs against a freshly created git worktree managed by `llm4ad.infra.version_control` (see [Infrastructure](infra.md)). This isolates concurrent individuals from each other without polluting the main repo; the worktree is garbage-collected after evaluation, while the `best/` directory keeps a copy of the top performer (cli.py:184).

`GenerateResult.working_dir` always points at the worktree root, and `generated_files` are relative to it. Pass the worktree path on to the evaluator as `EvalContext.project_root`:

```python
from llm4ad.coder.base import BaseCoder
from llm4ad.config.schema import EvalContext

BaseCoder.discover("llm4ad.coder")
coder = BaseCoder.create("custom", config=app_config.coder, provider=provider)

result = await coder.generate(algorithm, working_dir=str(worktree.path))
if result.is_success:
    ctx = EvalContext(project_root=result.working_dir, data_path="...", timeout=60.0)
```

## EVOLVE block replacement

Coders only edit code regions marked between `# EVOLVE_START` / `# EVOLVE_END`. Detection, cleanup, and active-block resolution are handled by `llm4ad.infra.repo_analyzer` (see [Infrastructure](infra.md) and [`llm4ad evolve check`/`evolve clean`](../guides/cli.md#evolve)).

`CustomCoder` uses unified-diff content mode: when an `Algorithm.code_artifacts[i].content_mode == "diff"`, the diff is applied to the current worktree file via `apply_unified_diff` (see [Utilities](utils.md)). This makes edits auditable and reversible.

## Choosing a coder

| Task | Recommended | Rationale |
|---|---|---|
| Single-file, well-marked EVOLVE block | `custom` | Fastest, cheapest, explainable (unified diff) |
| Multi-file or agent-style edits or free-form rewriting | `claude_code` or `opencode` | Lets the agent decide where to edit across files |
| Tests / CI / iterating on prompts | Any + `MockProvider` | End-to-end reproducible without real LLM calls |

Agent-style coders are separate install extras; see [Installation](../guides/installation.md).

## See also

- [Coder configuration](../guides/configuration.md#coder) — `coder:` block in YAML
- [CLI Reference](../guides/cli.md#evolve) — marker-block tooling
- Source of truth: `src/llm4ad/coder/`
