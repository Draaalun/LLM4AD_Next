# Evolve-Block Advisor

The **Evolve-Block Advisor** answers a narrower, faster question than the
builder or the main evolution pipeline:

> **"Is THIS block of code worth evolving for THIS goal?"**

It runs a single LLM call against one user-selected code block and
returns structured advice that a frontend can render next to the
selection *before* the user commits to an evolution run.

The advisor is independent of the builder, designed to be called
on-demand (for example, on every "analyze selection" click), and safe
to call repeatedly. Output is **JSON on stdout** by default so it can
be piped straight to a frontend.

---

## When to use it

| Situation | Use |
| --- | --- |
| User has already selected a block in the editor and clicked "analyze" | **Advisor** |
| User has only a repo + goal and needs help *choosing* a block | [**Recommender**](recommender.md) (which internally calls the advisor) |
| User wants a full runnable LLM4AD app built from scratch | **Builder** (`llm4ad build`) |

The advisor does **not** modify code, does **not** run evolution, and
does **not** write any files on its own. It is read-only.

---

## What the advisor returns

A single `BlockAdvice` object with these fields:

| Field | Type | Description |
| --- | --- | --- |
| `block_summary` | `string` | One to three sentences describing what the block does. |
| `feasibility` | `"yes" \| "partial" \| "no"` | Whether the goal is achievable by editing this block alone. |
| `feasibility_reason` | `string` | Short justification for the feasibility verdict. |
| `significance` | `"high" \| "medium" \| "low"` | How much impact editing this block is expected to have on the goal. |
| `significance_reason` | `string` | Short justification for the significance verdict. |
| `concerns` | `string[]` | Risks / pitfalls the user should know before evolving. |
| `suggestions` | `string[]` | Concrete, actionable refinements the user should consider. |
| `rationale` | `string` | One-paragraph overall assessment tying everything together. |

Shape is stable; `to_dict()` / JSON output is suitable for direct UI
consumption.

---

## CLI usage

### Basic: explicit block

```bash
llm4ad advise \
  --goal "minimize comparisons on random inputs" \
  --repo ./solver \
  --file algo.py \
  --range 42:87
```

`--range` is **1-based inclusive** (`START:END`).

### Repo with a single `# EVOLVE_START` / `# EVOLVE_END` block

If the repo already contains exactly one `EVOLVE`-marked block, you can
omit `--file` / `--range`:

```bash
llm4ad advise -g "reduce tour length" -r ./solver
```

The advisor auto-discovers the marked block. If there are zero or more
than one, it errors out instead of guessing.

### Raw snippet (no repo)

```bash
llm4ad advise -g "..." --code "$(cat patch.py)"
```

### Config-driven

```bash
# 1. Generate a filled-in template
llm4ad advise-init -o advise_config.yaml

# 2. Edit the YAML, then run
llm4ad advise --config advise_config.yaml
```

### Human-readable output

Add `--pretty` to render a Rich panel instead of raw JSON:

```bash
llm4ad advise -g "..." -r ./solver --file algo.py --range 42:87 --pretty
```

---

## Provider configuration

The advisor resolves credentials in this precedence (highest first):

1. **`--provider NAME`**: named provider from `~/.llm4ad/settings.yaml`
2. **Explicit flags**: `--api-key`, `--model`, `--base-url`, `--provider-type`
3. **Environment variables**:
   - `LLM4AD_ADVISE_API_KEY`
   - `LLM4AD_ADVISE_MODEL` (default: `gpt-4o`)
   - `LLM4AD_ADVISE_BASE_URL`

Tip: the advisor is cheap per call (typically one 2-4k-token request),
so it can reasonably run on a smaller / cheaper model than the main
pipeline.

---

## Python API

```python
from llm4ad.advisor import advise_block_sync

advice = advise_block_sync(
    goal="minimize comparisons on random inputs",
    repo_path="./solver",
    file_path="algo.py",
    line_range=(42, 87),
    api_key="sk-...",
    model="gpt-4o-mini",
)
print(advice.feasibility, advice.significance)
for concern in advice.concerns:
    print("-", concern)
```

Async variant:

```python
from llm4ad.advisor import advise_block

advice = await advise_block(
    goal="...",
    repo_path="./solver",
    file_path="algo.py",
    line_range=(42, 87),
    provider_name="my_cheap_provider",  # from ~/.llm4ad/settings.yaml
)
```

---

## Block resolution order

When you call the Python API, block selection follows the first matching
rule:

1. `evolve_block=...` passed directly (skip all detection).
2. `repo_path` + `file_path` + `line_range` (explicit location).
3. `repo_path` alone (repo must contain **exactly one** `EVOLVE` block).
4. `code=...` only (treat as an unlocated snippet).

---

## Advisor-config YAML

```yaml
# advise_config.yaml

advisor:
  type: "openai_compatible"                # openai | anthropic | openai_compatible
  api_key: "${LLM4AD_ADVISE_API_KEY}"
  base_url: "${LLM4AD_ADVISE_BASE_URL}"
  model: "gpt-4o-mini"

task:
  goal: |
    Reduce tour length on Euclidean TSP instances of 50-200 cities.
  repo_path: "./solver"
  file_path: "tsp_algorithm/solve.py"
  line_range: [14, 51]                     # 1-based inclusive
  # OR, for a standalone snippet:
  # code: |
  #   def solve(data):
  #       ...
```

`${ENV_VAR}` expansion is supported for every string field. Either
`repo_path` (with optional `file_path` + `line_range`) or `code` must
be present. If `repo_path` is given without a file/range, there must
be exactly one `EVOLVE` block in the repo.

---

## Output: full JSON example

```json
{
  "block_summary": "Nearest-neighbor TSP tour construction starting from city 0.",
  "feasibility": "yes",
  "feasibility_reason": "The block is a self-contained heuristic; replacing it with a better constructor or adding 2-opt/LKH-style post-processing directly addresses tour length.",
  "significance": "high",
  "significance_reason": "Tour-construction heuristic has a large effect on final length for 50-200 city instances.",
  "concerns": [
    "Replacing nearest-neighbor with a more expensive constructor may violate per-instance time budgets.",
    "Random-restart approaches need a deterministic seed for reproducible benchmarks."
  ],
  "suggestions": [
    "Add a 2-opt improvement pass after the greedy tour.",
    "Consider cheapest-insertion or Christofides-style construction as alternatives."
  ],
  "rationale": "The block is exactly where tour quality is decided, so edits here have a high ceiling. Feasibility is high because the interface (nodes -> tour) is narrow and stable. Main risks are runtime regressions and non-determinism."
}
```

---

## Frontend integration pattern

A typical "analyze selection" flow:

```
User selects lines 42–87 in algo.py
        │
        ▼
Frontend POSTs  { goal, repo_path, file_path, line_range }
        │
        ▼
Backend runs:  advise_block_sync(...)  (1 LLM call, ~2–5s)
        │
        ▼
Frontend receives JSON and renders:
  • green / yellow / red badge from `feasibility`
  • high / medium / low badge from `significance`
  • bullet list of `concerns`
  • bullet list of `suggestions`
  • collapsible `rationale`
  • "Evolve this block" CTA, enabled when feasibility != "no"
```

The advisor is stateless and each call is independent. Rate-limit on
the frontend by user selection / debounce; there is no cache layer
inside the advisor itself.

---

## Errors you should handle

The advisor raises `AdvisorError` for:

- Missing credentials (`advisor.api_key` empty, no env var, no named provider).
- Missing / empty `goal`.
- Ambiguous block (repo given but 0 or >1 `EVOLVE` blocks).
- File not found, line range out of bounds, or decode errors.

The CLI converts these to a red-boxed stderr message and exits with
code 1. The Python API lets them propagate. Catch `AdvisorError`
specifically; other exceptions indicate bugs / network issues.

```python
from llm4ad.advisor import advise_block_sync
from llm4ad.advisor.pipeline import AdvisorError

try:
    advice = advise_block_sync(goal=g, repo_path=r, file_path=f, line_range=rng)
except AdvisorError as e:
    return {"error": str(e)}, 400
```

---

## See also

- [Evolve-Block Recommender](recommender.md) — propose *which* block to evolve when the user has not selected one.
- [Quick Start](quickstart.md)
- [Providers](providers.md)
