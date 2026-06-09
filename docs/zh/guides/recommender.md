# Evolve-Block Recommender（演化块推荐器）

**Evolve-Block Recommender** 回答这个问题：

> **"我有一个仓库和一个目标——该演化哪个块？"**

它是用户带着一个仓库和一个算法演化目标、但**尚未选中具体代码块**时
的入口。一次 LLM 发现（discovery）调用会扫描仓库的压缩视图，返回
排好序的候选块，每个候选都已经过 [Advisor](advisor.md) 预打分。

内部流程：

```
仓库 + 目标
    │
    ▼
1. 压缩仓库 → 文件树 + 按目标排序的文件内容（带行号）
    │
    ▼
2. 一次"发现" LLM 调用 → 候选 {core, expanded, alternatives}
    │
    ▼
3. 校验候选（文件存在、行号合法、在仓库内等）
    │
    ▼
4. 对每个存活的候选 → 并发一次 Advisor 调用
    │
    ▼
5. 返回 RepoRecommendations（可 JSON 序列化）
```

---

## 三层输出

LLM4AD 的演化引擎目前**只支持单块演化**，因此推荐器不会给出一个需要
"一起演化"的块集合。它给出的是三种**备选**：

| 层级 | 数量 | 含义 |
| --- | --- | --- |
| `core` | 恰好 1 | 最有希望的最小块。 |
| `expanded` | 0–3 | `core` 的扩展变体（在同一文件里，例如把 `core` 调用的 helper 函数也包进来）。按 `size_lines` 升序排列。 |
| `alternatives` | 0–3 | 仓库内其他位置独立的候选块。 |

用户（或前端）选择**其中一个**交给后续演化。

---

## 何时使用

| 场景 | 使用 |
| --- | --- |
| 用户只有仓库 + 目标 | **Recommender** |
| 用户已经在编辑器里选中了代码块 | [**Advisor**](advisor.md)（更便宜，1 次 LLM 调用，而非 2–8 次） |
| 用户希望生成一个全新的、可直接运行的 LLM4AD 任务 | **Builder**（`llm4ad build`） |

Recommender 是只读的，不会修改文件、不会触发演化。

---

## 返回内容

### `RepoRecommendations`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `goal` | `string` | 传入的目标。 |
| `repo_path` | `string` | 被分析仓库的绝对路径。 |
| `core` | `BlockRecommendation \| null` | 核心推荐（成功时必然填充）。 |
| `expanded` | `BlockRecommendation[]` | `core` 的扩展变体，按大小升序。 |
| `alternatives` | `BlockRecommendation[]` | 其他位置的独立候选。 |
| `unreadable_files` | `string[]` | 压缩阶段被跳过的文件（解码 / 权限错误）。 |
| `dropped_candidates` | `object[]` | 校验失败的 LLM 建议；每项包含 `file_path`, `line_start`, `line_end`, `tier`, `reason`。 |
| `discovery_raw` | `string \| null` | 未解析的 LLM 原文，仅当 `include_raw=True` 时附加。 |

### `BlockRecommendation`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file_path` | `string` | 相对仓库根的路径（正斜杠）。 |
| `line_start` | `int` | 1-based 闭区间起始行。 |
| `line_end` | `int` | 1-based 闭区间结束行。 |
| `tier` | `"core" \| "expanded" \| "alternative"` | 所属层级。 |
| `variant_index` | `int \| null` | 在 `expanded` 中的顺序；core / alternatives 为 `null`。 |
| `size_lines` | `int` | `line_end - line_start + 1`。 |
| `discovery_rationale` | `string` | 发现阶段 LLM 给出的简短理由。 |
| `advice` | `BlockAdvice \| null` | Advisor 的打分结果。若该块的 advice 调用失败则为 `null`（其他块仍可能成功）。 |
| `advice_error` | `string \| null` | 当 `advice` 为 `null` 时记录的错误消息。 |

`BlockAdvice` 的结构见 [Advisor 指南](advisor.md)。

---

## CLI 用法

### 基本

```bash
llm4ad recommend \
  --goal "在随机欧氏实例上缩短 TSP 巡回长度" \
  --repo ./solver
```

默认**输出 JSON 到 stdout**，前端可直接消费。

### 人类可读输出

```bash
llm4ad recommend -g "..." -r ./solver --pretty
```

渲染成堆叠的 Rich 面板：每层一个面板，显示位置、理由，以及 Advisor 给出的
可行性 / 重要性 / 风险 / 建议。

### 调试发现阶段

加 `--include-raw`，响应里会带上发现阶段 LLM 的原文（在 `discovery_raw`）：

```bash
llm4ad recommend -g "..." -r ./solver --include-raw
```

候选进了 `dropped_candidates` 时特别有用——可以看出 LLM 实际写的是什么
路径 / 行号。

### 限制 advice 并发

默认最多 **5** 个 advice 并发（core + 最多 3 expanded + 最多 3 alternatives，
共计最多 7 次调用）。串行或放慢：

```bash
llm4ad recommend -g "..." -r ./solver --max-concurrency 1
```

---

## Provider 凭证解析

与 Advisor 完全一致，优先级（从高到低）：

1. `--provider NAME`（来自 `~/.llm4ad/settings.yaml` 的命名 provider）
2. `--api-key`, `--model`, `--base-url`, `--provider-type`
3. 环境变量：`LLM4AD_ADVISE_API_KEY`, `LLM4AD_ADVISE_MODEL`, `LLM4AD_ADVISE_BASE_URL`

Recommender 复用 Advisor 的凭证解析——一套 key / 设置同时驱动两个命令。

**成本提示**：一次请求最多触发 `1 + 3 + 3 = 7` 次 advice 调用再加一次
discovery 调用，所以 Recommender 的成本大约是一次 Advisor 的 **2–8 倍**。
没有明确的升级理由时，建议挂在小而便宜的模型上（`gpt-4o-mini`、
`claude-haiku-*`）。

---

## Python API

```python
from llm4ad.advisor import recommend_blocks_sync

result = recommend_blocks_sync(
    goal="缩短 TSP 巡回长度",
    repo_path="./solver",
    api_key="sk-...",
    model="gpt-4o-mini",
)

print("CORE:", result.core.file_path, result.core.line_start, "-", result.core.line_end)
print("  可行性:", result.core.advice.feasibility)

for alt in result.alternatives:
    print("ALT:", alt.file_path, alt.advice.significance if alt.advice else "?")

# 序列化用于传输 / 日志：
payload = result.to_dict()
```

异步版本：

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

## 仓库压缩：LLM 实际看到什么

对于一个有 100 个文件的仓库，把所有行都塞给 LLM 既浪费又往往超上下文。
Recommender 在发现调用之前会压缩仓库：

1. **收集**匹配 `*.py`, `*.cpp`, `*.c`, `*.cc`, `*.h`, `*.hpp`, `*.js`, `*.ts`, `*.java`, `*.go`, `*.rs` 的文件。
2. **排除**常见噪声：`__pycache__/`, `node_modules/`, `.git/`, `venv/`, `dist/`, `build/` 等。
3. **排序**剩余文件：
   - 路径或前 ~100 行是否命中目标关键字。
   - 文件名是否像入口（`algo.*`, `solver.*`, `main.*`, `solve.*` 等）。
   - 文件大小（小的靠前）。
4. **拟合**到字符预算里（默认约 180k 字符）。超过单文件预算的文件会被
   截断到头部，并附加 `# ...file truncated...` 标记。
5. **输出**内容，每一行前都加上**1-based 行号前缀**，以便 LLM 可以引用
   精确的行号范围，而 Recommender 后续会按同样的索引进行校验。

未能以 UTF-8 解码的文件会被记录到 `unreadable_files`，并从 prompt 中排除。

---

## 校验规则

Recommender 会在调用 Advisor 之前校验每个候选。校验失败的项目进入
`dropped_candidates`，带下列 `reason` 之一：

| `reason` | 含义 |
| --- | --- |
| `missing_file_path` | LLM 返回了空或非字符串的路径。 |
| `invalid_line_numbers` | `line_start` / `line_end` 无法解析为整数。 |
| `invalid_range` | `start < 1` 或 `end < start`。 |
| `escaped_repo` | 路径解析到仓库根之外（例如 `../other.py`）。 |
| `file_not_found` | 路径不存在（剥除可能的仓库名前缀幻觉后仍不存在）。 |
| `file_unreadable` | 读取失败（解码错误、权限不足）。 |
| `range_out_of_bounds` | `line_end` 超过文件总行数。 |
| `not_superset_of_core` | 某 `expanded` 变体的范围未严格包含 core。 |
| `overlaps_core` | 某 `alternative` 与 core 的范围重叠。 |

如果 **core** 本身校验失败，Recommender 会抛 `AdvisorError`，而不是返回
残缺结果。`expanded` / `alternative` 的失败只会被单独丢弃。

---

## 前端集成模式

```
用户粘贴目标，上传 / 选择仓库
        │
        ▼
前端 POST  { goal, repo_path }           （或把仓库打包上传）
        │
        ▼
后端执行  recommend_blocks_sync(...)
           • 1 次 discovery 调用
           • ≤7 次并发 advice 调用
           • 在 gpt-4o-mini 上总耗时约 5–30 秒
        │
        ▼
前端收到 JSON 并渲染：
  ┌──────────────────────────────┐
  │ CORE                         │  绿色边框
  │  file:行号范围               │
  │  可行性 / 重要性             │
  │  风险 / 建议                 │
  │  [演化此块]                  │
  └──────────────────────────────┘
  ┌──────────────────────────────┐
  │ EXPANDED 变体 1 / 2 / 3      │  青色边框
  │  file:行号范围               │
  │  同样的 advisor 字段         │
  │  [演化此块]                  │
  └──────────────────────────────┘
  ┌──────────────────────────────┐
  │ ALTERNATIVE 1 / 2 / 3        │  品红色边框
  │  （通常在不同文件）          │
  │  [演化此块]                  │
  └──────────────────────────────┘
```

用户选中哪个推荐，就按 `file_path[line_start..line_end]` 精确包裹一对
EVOLVE 标记生成演化配置。这是单块演化——LLM4AD 不会把多个 tier
合并去演化。

---

## 错误处理

| 错误 | 触发条件 | CLI 行为 |
| --- | --- | --- |
| `AdvisorError: Repo path does not exist: …` | `--repo` 指向不存在的路径 | 红色提示 + 退出码 1 |
| `AdvisorError: Repo path is not a directory: …` | `--repo` 指向文件 | 红色提示 + 退出码 1 |
| `AdvisorError: Recommender discovery returned unparseable JSON` | 发现阶段 LLM 破坏了输出契约 | 红色提示 + 退出码 1 |
| `AdvisorError: Core candidate failed validation: {…, 'reason': '…'}` | LLM 幻觉出一个不合法的 core 块 | 红色提示 + 退出码 1 |
| 凭证缺失 | 命令行 / 环境 / 全局设置中都没有 key | 红色提示 + 退出码 1 |

以上在 Python API 中都会以 `AdvisorError` 抛出。

**单个**块的 advice 调用失败永远**不会**让整个请求失败——受影响的
`BlockRecommendation` 只会留下 `advice=None` 和 `advice_error="..."`，
其余结果照常返回。

---

## 示例：TSP benchmark

```bash
export LLM4AD_ADVISE_API_KEY="sk-..."
export LLM4AD_ADVISE_BASE_URL="https://api.openai.com/v1/"

llm4ad recommend \
  -g "在随机欧氏实例上缩短 TSP 巡回长度" \
  -r examples/applications/tsp_benchmark_python \
  --model gpt-4o-mini \
  --pretty
```

预期形态：

- **Core**：`tsp_algorithm/solve.py:14-51` —— `nearest_neighbor_tsp` 函数
- **Expanded**：可能扩展到同时包含 `calculate_tour_length`
- **Alternatives**：有时会在 `tsp_evaluator.py` 里提出一个块（通常被 Advisor 判为重要性较低）

---

## 相关文档

- [Evolve-Block Advisor](advisor.md) —— 推荐器内部调用的单块打分器；
  当用户已经选中块时直接使用它。
- [快速入门](quickstart.md)
- [Provider 配置](providers.md)
