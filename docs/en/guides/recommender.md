# Evolve-Block Recommender

The **Evolve-Block Recommender** answers the question:

> **"I have a repo and a goal — which block should I evolve?"**

It is the entry point for users who arrive at the platform with a
repository and an algorithm-evolution goal but have **not yet picked a
specific block**. One LLM discovery call scans a compacted view of the
repo and returns ranked candidates, each pre-scored by the
[Advisor](advisor.md).

Internally the flow is:

```
repo + goal
    │
    ▼
1. Compact repo → file tree + goal-ranked file contents with line numbers
    │
    ▼
2. One "discovery" LLM call → candidates {core, expanded, alternatives}
    │
    ▼
3. Validate candidates (file exists, range valid, in-repo, etc.)
    │
    ▼
4. For each surviving candidate → one parallel Advisor call
    │
    ▼
5. Return RepoRecommendations (JSON-serializable)
```

---

## Three-tier output

LLM4AD's evolution engine is **single-block-only** today, so the
recommender does *not* propose a bundle to co-evolve. Instead it gives
three alternative **choices**:

| Tier | Cardinality | What it is |
| --- | --- | --- |
| `core` | exactly 1 | The single most promising minimal block. |
| `expanded` | 0–3 | Widenings of `core` in the same file (e.g., include the helper function that `core` calls). Sorted by `size_lines` ascending. |
| `alternatives` | 0–3 | Independent candidate blocks in other locations in the repo. |

The user (or the frontend) picks **one** to hand off to evolution.

---

## When to use it

| Situation | Use |
| --- | --- |
| User only has a repo + goal | **Recommender** |
| User already selected a block in the editor | [**Advisor**](advisor.md) (cheaper, ~1 LLM call instead of 2–8) |
| User wants a brand-new runnable LLM4AD task generated | **Builder** (`llm4ad build`) |

The recommender is read-only. It does not modify files or run
evolution.

---

## What the recommender returns

### `RepoRecommendations`

| Field | Type | Description |
| --- | --- | --- |
| `goal` | `string` | The goal you passed in. |
| `repo_path` | `string` | Absolute path of the analyzed repo. |
| `core` | `BlockRecommendation \| null` | The core recommendation (populated on success). |
| `expanded` | `BlockRecommendation[]` | Widenings of core, sorted smallest first. |
| `alternatives` | `BlockRecommendation[]` | Independent blocks elsewhere. |
| `unreadable_files` | `string[]` | Files skipped during compaction (decode / permission errors). |
| `dropped_candidates` | `object[]` | LLM suggestions that failed validation; each entry carries `file_path`, `line_start`, `line_end`, `tier`, `reason`. |
| `discovery_raw` | `string \| null` | Unparsed LLM text, attached only when `include_raw=True`. |

### `BlockRecommendation`

| Field | Type | Description |
| --- | --- | --- |
| `file_path` | `string` | Repo-relative path (forward slashes). |
| `line_start` | `int` | 1-based inclusive start line. |
| `line_end` | `int` | 1-based inclusive end line. |
| `tier` | `"core" \| "expanded" \| "alternative"` | Which tier this belongs to. |
| `variant_index` | `int \| null` | Sort order within `expanded`; `null` for core / alternatives. |
| `size_lines` | `int` | `line_end - line_start + 1`. |
| `discovery_rationale` | `string` | Short justification from the discovery LLM. |
| `advice` | `BlockAdvice \| null` | Phase-1 advisor output. `null` if advice enrichment failed for this block specifically (other blocks may still succeed). |
| `advice_error` | `string \| null` | Error message recorded when `advice` is `null`. |

See the [Advisor guide](advisor.md) for the shape of `BlockAdvice`.

---

## CLI usage

### Basic

```bash
llm4ad recommend \
  --goal "reduce TSP tour length on random Euclidean instances" \
  --repo ./solver
```

Default output is **JSON on stdout** for direct frontend consumption.

### Human-readable

```bash
llm4ad recommend -g "..." -r ./solver --pretty
```

Renders stacked Rich panels: one per tier, each showing location,
rationale, and the advisor's feasibility / significance / concerns /
suggestions.

### Debugging the discovery call

Add `--include-raw` to return the discovery LLM's verbatim output under
`discovery_raw`:

```bash
llm4ad recommend -g "..." -r ./solver --include-raw
```

Particularly useful when candidates end up in `dropped_candidates` —
the raw output lets you see what path / range the LLM actually
proposed.

### Limiting advice parallelism

By default up to **5** advice calls run concurrently (the core + up to
3 expanded + up to 3 alternatives means at most 7 calls). To
serialize or slow it down:

```bash
llm4ad recommend -g "..." -r ./solver --max-concurrency 1
```

---

## Provider configuration

Identical to the advisor. Precedence (highest first):

1. `--provider NAME` (named provider from `~/.llm4ad/settings.yaml`)
2. `--api-key`, `--model`, `--base-url`, `--provider-type`
3. Env vars: `LLM4AD_ADVISE_API_KEY`, `LLM4AD_ADVISE_MODEL`, `LLM4AD_ADVISE_BASE_URL`

The recommender reuses the advisor's credential resolution — a single
set of keys / settings drives both commands.

**Cost note.** One request fires at most `1 + 3 + 3 = 7` advice calls
plus one discovery call, so the recommender is **~2×–8×** the cost of
one advisor call. Use a small, cheap model (`gpt-4o-mini`,
`claude-haiku-*`) unless you have reason to upgrade.

---

## Python API

```python
from llm4ad.advisor import recommend_blocks_sync

result = recommend_blocks_sync(
    goal="reduce TSP tour length",
    repo_path="./solver",
    api_key="sk-...",
    model="gpt-4o-mini",
)

print("CORE:", result.core.file_path, result.core.line_start, "-", result.core.line_end)
print("  feasibility:", result.core.advice.feasibility)

for alt in result.alternatives:
    print("ALT:", alt.file_path, alt.advice.significance if alt.advice else "?")

# Serialize for transport / logging:
payload = result.to_dict()
```

Async variant:

```python
from llm4ad.advisor import recommend_blocks

result = await recommend_blocks(
    goal="...",
    repo_path="./solver",
    provider_name="my_cheap_provider",
    max_concurrency=3,
    include_raw=True,
)
```

---

## Repo compaction: what the LLM actually sees

For a 100-file repo sending every line to the LLM would be wasteful
and often exceed context limits. The recommender compacts the repo
before the discovery call:

1. **Collect** files matching `*.py`, `*.cpp`, `*.c`, `*.cc`, `*.h`, `*.hpp`, `*.js`, `*.ts`, `*.java`, `*.go`, `*.rs`.
2. **Exclude** common noise: `__pycache__/`, `node_modules/`, `.git/`, `venv/`, `dist/`, `build/`, etc.
3. **Rank** remaining files by:
   - Whether keywords from the goal appear in the path or the first ~100 lines.
   - Whether the name looks like an entrypoint (`algo.*`, `solver.*`, `main.*`, `solve.*`, etc.).
   - File size (smaller goes first).
4. **Fit** files into a char budget (default ~180k chars). Files
   exceeding a per-file budget are truncated to the head with a
   `# ...file truncated...` marker.
5. **Emit** contents with **1-based line numbers prefixed** to every
   line, so the LLM can cite exact ranges that the recommender will
   later validate against the same indexing.

Files that fail to decode as UTF-8 are recorded in
`unreadable_files` and excluded from the prompt.

---

## Validation rules

The recommender validates every candidate before invoking the advisor.
Failures go to `dropped_candidates` with one of these reasons:

| `reason` | Meaning |
| --- | --- |
| `missing_file_path` | LLM returned an empty / non-string path. |
| `invalid_line_numbers` | `line_start` / `line_end` not parseable as ints. |
| `invalid_range` | `start < 1` or `end < start`. |
| `escaped_repo` | Path resolves outside the repo root (e.g., `../other.py`). |
| `file_not_found` | Path doesn't exist (even after stripping a hallucinated repo-name prefix). |
| `file_unreadable` | Read failed (decode error, permission denied). |
| `range_out_of_bounds` | `line_end` exceeds the file's line count. |
| `not_superset_of_core` | An `expanded` variant's range doesn't strictly contain core's. |
| `overlaps_core` | An `alternative` overlaps core's range. |

If the **core** candidate itself fails any of these checks, the
recommender raises `AdvisorError` rather than returning a partial
result. For `expanded` / `alternative` failures the recommender just
drops the offending item.

---

## Frontend integration pattern

```
User pastes a goal and uploads / selects a repo
        │
        ▼
Frontend POSTs  { goal, repo_path }           (or uploads the repo as a tarball)
        │
        ▼
Backend runs:  recommend_blocks_sync(...)
                 • 1 discovery call
                 • ≤7 parallel advice calls
                 • ~5–30s total wall time on gpt-4o-mini
        │
        ▼
Frontend receives JSON and renders:
  ┌──────────────────────────────┐
  │ CORE                         │  green border
  │  file:line range             │
  │  feasibility / significance  │
  │  concerns / suggestions      │
  │  [Evolve this block]         │
  └──────────────────────────────┘
  ┌──────────────────────────────┐
  │ EXPANDED variant 1 / 2 / 3   │  cyan border
  │  file:line range             │
  │  same advisor fields         │
  │  [Evolve this block]         │
  └──────────────────────────────┘
  ┌──────────────────────────────┐
  │ ALTERNATIVE 1 / 2 / 3        │  magenta border
  │  (different file usually)    │
  │  [Evolve this block]         │
  └──────────────────────────────┘
```

Picking any recommendation should produce an evolution config whose
EVOLVE markers wrap exactly `file_path[line_start..line_end]`. That is
a single-block evolution — LLM4AD does not co-evolve the tiers.

---

## Error handling

| Error | When it fires | What the CLI does |
| --- | --- | --- |
| `AdvisorError: Repo path does not exist: …` | `--repo` pointed at nothing | Red banner + exit 1 |
| `AdvisorError: Repo path is not a directory: …` | `--repo` was a file | Red banner + exit 1 |
| `AdvisorError: Recommender discovery returned unparseable JSON` | Discovery LLM broke the output contract | Red banner + exit 1 |
| `AdvisorError: Core candidate failed validation: {…, 'reason': '…'}` | LLM hallucinated an invalid core block | Red banner + exit 1 |
| Missing credentials | No key from flags / env / settings | Red banner + exit 1 |

All of these surface as `AdvisorError` in the Python API.

Advice-enrichment failures for an **individual** block never fail the
whole request — the affected `BlockRecommendation` just gets
`advice=None` and `advice_error="..."`, and the rest of the result is
returned normally.

---

## Example: TSP benchmark

```bash
export LLM4AD_ADVISE_API_KEY="sk-..."
export LLM4AD_ADVISE_BASE_URL="https://api.openai.com/v1/"

llm4ad recommend \
  -g "reduce TSP tour length on random Euclidean instances" \
  -r examples/applications/tsp_benchmark_python \
  --model gpt-4o-mini \
  --pretty
```

Expected shape:

- **Core**: `tsp_algorithm/solve.py:14-51` — the `nearest_neighbor_tsp` function
- **Expanded**: possibly widens to include `calculate_tour_length` too
- **Alternatives**: sometimes proposes a block in `tsp_evaluator.py` (but lower-impact, usually flagged low-significance by the advisor)

---

## See also

- [Evolve-Block Advisor](advisor.md) — the per-block scorer called
  internally by the recommender; use directly when the user has already
  selected a block.
- [Quick Start](quickstart.md)
- [Providers](providers.md)
