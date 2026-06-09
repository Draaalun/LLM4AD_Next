# Embeddings 与轨迹

LLM4AD 在两个地方用嵌入：算法间的相似度比较（用于 DyCA 聚类、MEoH 多样性惩罚、3D HTML 轨迹可视化），以及 `consultant` / `advisor` / `recommender` 中的语义检索。本页解释相关配置与注意事项。

## `embedding:` 块

`embedding:` 在 `AppConfig` 顶层，由 `EmbeddingConfig`（`src/llm4ad/config/app.py`）定义。

```yaml
embedding:
  type: "openai_compatible"
  base_url: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"
  dim: 1536                 # 与 model 维度对齐
  embedding_func_max_async: 4   # 最大并发请求数
```

支持的 `type`：

| 值 | 何时用 |
|---|---|
| `openai` | 官方 OpenAI |
| `openai_compatible` | OpenAI 兼容端点（Together、vLLM、本地 sgpt 等） |
| `jina` | Jina embeddings |
| `mock` | 测试 / CI（确定性零向量） |
| `local` | 双端点模式 — 文本和代码可走不同部署 |

## `local` 模式：文本与代码分流

某些场景下，文本嵌入（用于查找相关文档、对话历史）和代码嵌入（用于算法相似度）希望走不同的模型甚至不同的端点。`local` 模式（PR #90）通过两个子配置实现这一点：

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

子配置中省略的字段会回退到顶层默认值。运行时，`EmbeddingClient.embed(text, task=...)` 根据 `task`（`"text"` 或 `"code"`）选择对应端点。

## 批量嵌入

PR #88 引入了批量嵌入。以一次请求覆盖多条文本能显著降低 LLM 服务的请求开销，对算法轨迹和大语料尤为重要。

`embedding_func_max_async` 控制最大并发批次数。客户端会自动按服务限制（如 OpenAI 默认 100 条/请求）分批；用户配置只需关心并发上限。

## 相似度的用法

| 用途 | 来自 |
|---|---|
| **DyCA 聚类** | 算法行为向量（锚点求得） |
| **MEoH 多样性惩罚** | 候选代码字符串的 CodeBLEU + 嵌入 |
| **3D HTML 轨迹** | 每个个体的算法嵌入 → UMAP 投影 → 3D 散点 |
| **Consultant 检索** | 历史对话片段语义查找 |
| **Advisor / Recommender** | 仓库代码 / 历史建议的语义查找 |

## 3D 轨迹可视化

PRs #78–#79 增加了"算法嵌入流水线 + 3D HTML 轨迹"。每次运行结束（或在 Web UI"快速分析"中）都会产出一份独立的 HTML 文件，展示算法在嵌入空间的演化轨迹。文件落在运行目录的 `state/` 下；Web UI 读取它来渲染交互式图表。

要启用，确保 `embedding:` 已配置，且至少 `evolution.max_generations >= 3` 让轨迹有足够的点。

## 调参建议

- **维度（`dim`）必须匹配模型**。设错会触发运行时校验错误。常见值：`text-embedding-3-small` = 1536，`text-embedding-3-large` = 3072。
- **`embedding_func_max_async`**：从 2–4 起步。LLM 服务限流时再调小。
- **MockProvider 测试**：单测建议设 `embedding.type: "mock"`，避免真实 API 调用。
- **本地部署**：如果用 sgpt / nomic / bge 自托管，用 `local` 模式把代码端点单独指向代码专用模型（如 `code-embed-v1` 或 `BAAI/bge-code-v1`），效果通常更好。

## 相关链接

- [Provider API](../api/provider.md) — 嵌入与 chat provider 的注册结构
- [DyCA](dyca.md) — 嵌入如何驱动聚类
- [配置指南](configuration.md) — 完整字段表
- 源码：`src/llm4ad/orchestrator/embedding_client.py`、`src/llm4ad/orchestrator/embedding_utils.py`
