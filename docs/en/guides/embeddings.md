# Embeddings & Trajectory

LLM4AD uses embeddings in two places: similarity comparisons between algorithms (powering DyCA clustering, MEoH diversity penalties, and the 3D HTML trajectory visualizer), and semantic retrieval inside `consultant` / `advisor` / `recommender`. This page covers configuration and tradeoffs.

## The `embedding:` block

`embedding:` lives at the top level of `AppConfig`, defined by `EmbeddingConfig` (`src/llm4ad/config/app.py`).

```yaml
embedding:
  type: "openai_compatible"
  base_url: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"
  dim: 1536                 # must match the model
  embedding_func_max_async: 4   # concurrency cap
```

Supported `type`:

| Value | When to use |
|---|---|
| `openai` | Official OpenAI |
| `openai_compatible` | OpenAI-compatible endpoints (Together, vLLM, self-hosted sgpt, …) |
| `jina` | Jina embeddings |
| `mock` | Tests / CI (deterministic zero-vectors) |
| `local` | Dual-endpoint mode — text and code can target different deployments |

## `local` mode: split text and code

In some setups, text embeddings (for finding relevant docs, conversation history) and code embeddings (for algorithm similarity) want to go through different models or even different endpoints. `local` mode (PR #90) supports this with two sub-configs:

```yaml
embedding:
  type: "local"
  text_config:
    base_url: "http://text-embed:8000/v1"
    api_key: "${TEXT_EMBED_KEY}"
    model: "bge-large-en-v1.5"
  code_config:
    base_url: "http://code-embed:8001/v1"
    api_key: "${CODE_EMBED_KEY}"
    model: "code-embedding-v1"
```

Fields omitted from a sub-config fall back to the top-level defaults. At runtime, `EmbeddingClient.embed(text, task=...)` picks the right endpoint based on `task` (`"text"` or `"code"`).

## Batched embeddings

PR #88 introduced batched embedding requests. Issuing one HTTP request covering many texts substantially reduces overhead, which matters for algorithm trajectories and large corpora.

`embedding_func_max_async` caps concurrent batches. The client automatically chunks by the service's per-request limit (OpenAI defaults to 100 inputs); users only need to worry about the concurrency cap.

## Where similarity is used

| Use | Source |
|---|---|
| **DyCA clustering** | Algorithm behavior vectors (computed via anchors) |
| **MEoH diversity penalty** | Candidate code string CodeBLEU + embedding |
| **3D HTML trajectory** | Per-individual algorithm embeddings → UMAP → 3D scatter |
| **Consultant retrieval** | Semantic lookup over past conversation snippets |
| **Advisor / Recommender** | Semantic lookup over repo code and prior advice |

## 3D trajectory visualization

PRs #78–#79 added the "algorithm embedding pipeline + 3D HTML trajectory". A standalone HTML file is produced at end of run (and live in the Web UI "rapid analysis" view) that shows the algorithm's evolution path in embedding space. The file lands in `state/` under the run directory; the Web UI reads it to render the interactive chart.

To enable, configure `embedding:` and run at least `evolution.max_generations >= 3` so the trajectory has enough points to plot.

## Tuning advice

- **`dim` must match the model**. A wrong value triggers a runtime validation error. Common: `text-embedding-3-small` = 1536, `text-embedding-3-large` = 3072.
- **`embedding_func_max_async`**: start at 2–4. Reduce if your embedding service rate-limits.
- **MockProvider for tests**: set `embedding.type: "mock"` in unit tests to avoid real API calls.
- **Self-hosted**: with sgpt / nomic / bge under `local` mode, point `code_config` at a code-specialized model (e.g. `BAAI/bge-code-v1`) for noticeably better algorithm clustering.

## See also

- [Provider API](../api/provider.md) — registry shape shared by embedding and chat providers
- [DyCA](dyca.md) — how embeddings drive clustering
- [Configuration Guide](configuration.md) — full field reference
- Source: `src/llm4ad/orchestrator/embedding_client.py`, `src/llm4ad/orchestrator/embedding_utils.py`
