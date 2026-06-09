# Evolve-Block Advisor（演化块顾问）

**Evolve-Block Advisor** 回答一个比 Builder 或主进化流水线都要
狭窄、快速的问题：

> **"这个代码块，针对这个目标，值得演化吗？"**

它对用户选中的**一个代码块**发起一次 LLM 调用，返回结构化的分析结果
——前端可以在用户点击"开始演化"**之前**，把这些结果渲染在选中代码旁边。

Advisor 独立于 Builder，设计为按需调用（例如前端每次"分析选中"时触发），
可重复调用无副作用。默认**输出 JSON 到 stdout**，前端可以直接拿去消费。

---

## 何时使用

| 场景 | 使用 |
| --- | --- |
| 用户已经在编辑器里选好了一段代码，点击"分析" | **Advisor** |
| 用户只有仓库 + 目标，还需要决定**选哪一块** | [**Recommender**](recommender.md)（它内部会调用 Advisor） |
| 用户想从零开始生成一个完整可运行的 LLM4AD 应用 | **Builder**（`llm4ad build`） |

Advisor **不会**修改代码、**不会**触发演化、**不会**自己写任何文件。
它是只读的。

---

## 返回内容

一个 `BlockAdvice` 对象，包含以下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `block_summary` | `string` | 用 1–3 句话描述这个代码块做什么。 |
| `feasibility` | `"yes" \| "partial" \| "no"` | 仅靠编辑这个块是否能达成目标。 |
| `feasibility_reason` | `string` | 可行性判断的简短依据。 |
| `significance` | `"high" \| "medium" \| "low"` | 编辑这个块对目标的预期影响程度。 |
| `significance_reason` | `string` | 重要性判断的简短依据。 |
| `concerns` | `string[]` | 演化之前用户应该关注的风险 / 坑。 |
| `suggestions` | `string[]` | 具体、可操作的改进建议。 |
| `rationale` | `string` | 一段总体评估，把以上内容串起来。 |

字段结构稳定，`to_dict()` 或 JSON 输出可以直接给前端使用。

---

## CLI 用法

### 基本：显式指定代码块

```bash
llm4ad advise \
  --goal "减少随机输入下的比较次数" \
  --repo ./solver \
  --file algo.py \
  --range 42:87
```

`--range` 是 **1-based 闭区间**（`START:END`）。

### 仓库中恰好有一个 `# EVOLVE_START` / `# EVOLVE_END` 块

如果仓库里已经标注了恰好一个 `EVOLVE` 块，可以省略 `--file` / `--range`：

```bash
llm4ad advise -g "缩短巡回长度" -r ./solver
```

Advisor 会自动发现被标记的块。如果标记块的数量是 0 或 >1，会直接报错，
不会猜。

### 裸代码片段（不依赖仓库）

```bash
llm4ad advise -g "..." --code "$(cat patch.py)"
```

### 基于配置文件

```bash
# 1. 生成已填好骨架的模板
llm4ad advise-init -o advise_config.yaml

# 2. 编辑 YAML，然后运行
llm4ad advise --config advise_config.yaml
```

### 人类可读输出

加 `--pretty` 用 Rich 面板渲染而不是裸 JSON：

```bash
llm4ad advise -g "..." -r ./solver --file algo.py --range 42:87 --pretty
```

---

## Provider 凭证解析

Advisor 按如下优先级解析凭证（从高到低）：

1. **`--provider NAME`**：`~/.llm4ad/settings.yaml` 里的命名 provider
2. **显式参数**：`--api-key`, `--model`, `--base-url`, `--provider-type`
3. **环境变量**：
   - `LLM4AD_ADVISE_API_KEY`
   - `LLM4AD_ADVISE_MODEL`（默认 `gpt-4o`）
   - `LLM4AD_ADVISE_BASE_URL`

提示：Advisor 每次调用很便宜（通常一次 2–4k token 请求），可以挂在比
主流水线更小、更便宜的模型上。

---

## Python API

```python
from llm4ad.advisor import advise_block_sync

advice = advise_block_sync(
    goal="减少随机输入下的比较次数",
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

异步版本：

```python
from llm4ad.advisor import advise_block

advice = await advise_block(
    goal="...",
    repo_path="./solver",
    file_path="algo.py",
    line_range=(42, 87),
    provider_name="my_cheap_provider",  # 来自 ~/.llm4ad/settings.yaml
)
```

---

## 代码块解析顺序

调用 Python API 时，代码块按下列规则选择（第一条命中的规则胜出）：

1. 直接传 `evolve_block=...`（跳过所有探测）。
2. `repo_path` + `file_path` + `line_range`（显式位置）。
3. 仅传 `repo_path`（仓库中必须**恰好一个** `EVOLVE` 块）。
4. 仅传 `code=...`（当作无位置的片段处理）。

---

## Advisor 配置 YAML

```yaml
# advise_config.yaml

advisor:
  type: "openai_compatible"                # openai | anthropic | openai_compatible
  api_key: "${LLM4AD_ADVISE_API_KEY}"
  base_url: "${LLM4AD_ADVISE_BASE_URL}"
  model: "gpt-4o-mini"

task:
  goal: |
    针对 50–200 个城市的欧氏 TSP 实例，缩短巡回长度。
  repo_path: "./solver"
  file_path: "tsp_algorithm/solve.py"
  line_range: [14, 51]                     # 1-based 闭区间
  # 或者使用独立片段：
  # code: |
  #   def solve(data):
  #       ...
```

每个字符串字段都支持 `${ENV_VAR}` 展开。`repo_path`（可选配合
`file_path` + `line_range`）和 `code` 必须至少有一个。如果只给了
`repo_path` 而没给 file/range，仓库里必须恰好有一个 `EVOLVE` 块。

---

## JSON 输出示例

```json
{
  "block_summary": "从城市 0 出发的最近邻 TSP 巡回构造。",
  "feasibility": "yes",
  "feasibility_reason": "这是一个自包含的启发式；用更好的构造器替换它，或追加 2-opt/LKH 风格的后处理，都能直接改善巡回长度。",
  "significance": "high",
  "significance_reason": "构造启发式对 50–200 城市实例的最终长度影响很大。",
  "concerns": [
    "用更昂贵的构造器替换最近邻可能会超过每个实例的时间预算。",
    "随机重启方法需要确定的随机种子才能复现基准。"
  ],
  "suggestions": [
    "在贪心巡回后追加一次 2-opt 改进。",
    "考虑 cheapest-insertion 或 Christofides 风格的构造作为备选。"
  ],
  "rationale": "这个块正是决定巡回质量的地方，因此编辑空间很大。接口稳定（nodes -> tour），可行性高。主要风险是运行时回退和非确定性。"
}
```

---

## 前端集成模式

典型的"分析选中"流程：

```
用户在 algo.py 选中第 42–87 行
        │
        ▼
前端 POST  { goal, repo_path, file_path, line_range }
        │
        ▼
后端执行  advise_block_sync(...)   （1 次 LLM 调用，约 2–5 秒）
        │
        ▼
前端收到 JSON 并渲染：
  • 根据 feasibility 显示绿/黄/红徽章
  • 根据 significance 显示高/中/低徽章
  • concerns 列表
  • suggestions 列表
  • 可折叠的 rationale
  • "演化此块"按钮，当 feasibility != "no" 时启用
```

Advisor 无状态，每次调用独立。前端按用户选择 / debounce 做限流即可；
advisor 内部没有缓存层。

---

## 你需要处理的错误

Advisor 在以下情况抛出 `AdvisorError`：

- 缺凭证（`advisor.api_key` 为空，且无环境变量、无命名 provider）。
- `goal` 缺失或为空。
- 代码块不明确（给了 repo，但 `EVOLVE` 块数量为 0 或 >1）。
- 文件不存在、行号越界、或解码错误。

CLI 会把这些渲染成红框 stderr 消息并以退出码 1 退出。Python API 则
让它们向上传播。**专门捕获 `AdvisorError`**，其他异常表示 bug 或网络问题。

```python
from llm4ad.advisor import advise_block_sync
from llm4ad.advisor.pipeline import AdvisorError

try:
    advice = advise_block_sync(goal=g, repo_path=r, file_path=f, line_range=rng)
except AdvisorError as e:
    return {"error": str(e)}, 400
```

---

## 相关文档

- [Evolve-Block Recommender](recommender.md) —— 用户还没选块时，推荐该**选哪一块**。
- [快速入门](quickstart.md)
- [Provider 配置](providers.md)
