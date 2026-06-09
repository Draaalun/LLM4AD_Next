# 自动构建（`llm4ad chat`）

自动构建器从一段自然语言描述出发生成一个完整、可直接运行的 LLM4AD 应用。CLI 命令是 `llm4ad chat`（`llm4ad build` 与 `llm4ad build-init` 已在 [#93](https://github.com/llm4ad/llm4ad/pull/93) 中合并入 `chat`）。Python builder API（`build_task_sync`、`build_from_config`、`build_from_config_sync`）保持稳定，是后端集成实际调用的接口。

本页讲工作流、自修复行为，以及 CLI 与 Python 两种使用方式。

## 它产出什么

给定描述：

> "进化排序算法，最小化比较次数和执行时间"

builder 会产出一个完整的应用目录：

```
{task_dir}/
├── config.yaml                    # 流水线配置
├── {project_name}_evaluator.py    # 含指标定义的自定义评估器
├── {algorithm_dir}/{algorithm}.py # 含 EVOLVE 标记的算法模板
├── debug_run.py                   # 快速本地测试脚本
├── test_evaluator.py              # 评估器端到端校验
├── data/sample/                   # 示例测试数据
└── blueprint_meta.json            # 构建元数据
```

构建完成后立即可以 `llm4ad run {task_dir}/config.yaml`。

## 四阶段流水线

1. **分析（`TaskAnalyzer`）** — 从自然语言中抽取任务结构：函数签名、指标、输入/输出格式、是否多模态。
2. **创建（`TaskCreator`）** — 生成评估器代码、含 EVOLVE 标记的算法模板、配置 YAML、debug 脚本、test_evaluator、示例数据。
3. **校验（`TaskValidator`）** — 运行静态检查（语法、配置结构、EVOLVE 标记、多模态 import）和运行时检查（import、算法试跑、debug_run、test_evaluator）。失败时把错误路由到正确的产物，让 LLM 仅修复那一个产物。
4. **写入（`TaskWriter`）** — 把校验通过的 blueprint 落盘。

### 校验阶段表

| 阶段 | 检查项 | 修复目标 |
|---|---|---|
| 1 | Python 语法（evaluator、algorithm、debug_run、test_evaluator） | 对应产物 |
| 2 | 配置 YAML 结构 | 全量重生成 |
| 3 | EVOLVE 标记存在 | 算法代码 |
| 4 | 多模态 import（启用时） | 评估器代码 |
| 5 | 评估器模块可 import、类存在 | 评估器代码 |
| 6 | 算法在示例数据上能跑 | 算法或数据集 |
| 7 | `debug_run.py` 可执行 | debug_run 代码 |
| 8 | `test_evaluator.py` 通过 | 评估器 + test_evaluator |

校验器**会聪明地路由错误**：算法阶段的 JSON 解析错误会指向数据集而非算法；同样错误重复出现会升级为整体重生成。在 `max_repair_attempts` 次（默认 3）失败后，构建会以 `BuildError` 终止。

## CLI 用法

```bash
# 完整多轮对话式构建
llm4ad chat

# 跳过 Phase 1 对话：直接给描述
llm4ad chat --prompt "进化排序算法，最小化比较次数"

# 完全非交互（CI / 批量场景）
llm4ad chat --prompt "进化排序" --non-interactive

# 在已有代码上改造而非从零开始
llm4ad chat --prompt "改进这个启发式" \
  --code-path ./solver/ --data-path ./data/

# 使用 ~/.llm4ad/settings.yaml 中的命名 provider
llm4ad chat --provider my-deepseek

# 恢复保存的会话
llm4ad chat --resume <session-id>
llm4ad chat --list-sessions
```

完整 flag 列表见 [CLI 参考](cli.md#chat)。

构建完成后，`llm4ad chat` 会询问是否立刻运行生成的流水线。

## Python API

```python
from llm4ad.builder import build_from_config_sync, build_from_config

# 同步（脚本 / Notebook）
task_dir = build_from_config_sync("build_config.yaml")

# 异步（FastAPI / web 后端）
task_dir = await build_from_config("build_config.yaml")

# 然后跑生成的流水线
from llm4ad import LLM4AD
llm4ad = LLM4AD(f"{task_dir}/config.yaml")
result = await llm4ad.run()
```

要嵌入到多租户 web 平台，详见[前端集成](../web-ui/frontend-integration.md) — 那里讲了异步 / 队列模式、轮询、安全和完整的 FastAPI 例子。

## `build_config.yaml` 格式

不希望靠 CLI flag 传所有参数时，用配置文件：

```yaml
builder:
  type: "openai_compatible"
  base_url: "${LLM4AD_BUILD_BASE_URL}"
  api_key: "${LLM4AD_BUILD_API_KEY}"
  model: "gpt-4o"
  max_repair_attempts: 3

task:
  description: |
    进化排序算法，最小化比较次数和执行时间。
    输入：整数列表。
    输出：有序列表。
  output_dir: "./output/"
  project_name: "my_task"
  multimodal: false
  visualization_hint: ""
```

然后：

```bash
llm4ad chat --prompt "$(cat task_description.md)" --output ./my_tasks/
# 或以编程方式：
build_from_config_sync("build_config.yaml")
```

字符串值中的 `${VAR_NAME}` 会在加载时根据进程环境变量展开。

## 生成的 `test_evaluator.py`

它不是一个语法检查脚本，而是一个完整的运行时测试：

- 导入评估器类，
- 加载示例数据，
- 用真实的 `EvalContext` 调 `evaluate()`，
- 校验期望指标存在，
- 打印 `[PASS]` / `[FAIL]`，并以对应 exit code 退出。

这才是"评估器在校验阶段确实能用"的硬保证，而不仅仅是"它能 parse"。

## 多模态构建

当 `task.multimodal: true`：

- 评估器脚手架通过 `BehaviorData` 返回可视化图像。
- 串好 `behavior_storage` 参数处理。
- 渲染器钩子被预留出来。
- `test_evaluator.py` 在 `EvalContext` 上传 `behavior_storage="rendered"`，触发多模态路径。

详见[多模态](multimodal.md)。

## 最佳实践

### 用户

1. **描述要具体** — 输入/输出格式、评分标准、约束。模糊描述会得到脆弱的脚手架。
2. **用环境变量装 API key**（`LLM4AD_BUILD_API_KEY` 等），不要在配置里写死。
3. **先本地跑通** — 在真正进化前先 `python {task_dir}/debug_run.py`。
4. **审一下生成代码** — builder 不错但不完美，重点看评估器逻辑。

### 平台集成方

1. **走配置驱动**：从前端表单生成 `build_config.yaml`，再调 `build_from_config()`。
2. **隔离用户构建**：每用户独立目录（`/data/builds/{user_id}/{task_id}/`）。
3. **走异步**：`build_from_config()`（async）适合 FastAPI；`_sync` 会阻塞数分钟。
4. **监控修复次数**：把校验错误日志化，发现重复失败模式。
5. **设硬超时**：构建一般 2–5 分钟，最多 10 分钟兜底。

## 局限

- **质量取决于 builder LLM** — 推荐 `gpt-4o` 或同档模型。
- **复杂评估逻辑** 构建后可能仍要人工微调。
- **领域知识** 是尽力而为 — 经典算法任务（排序、TSP、ML 超参）效果好于冷门领域。
- **3 次修复失败后**需要人工介入（构建抛 `BuildError`）。

## 参考样例

`examples/auto_applications/` 提供：

- `from_code/` — 在已有代码上改造（TSP、CVRP）
- `from_description/` — 从自然语言开始（bipedal_walker、CVRP）
- `build_config.yaml` 模板与对应输出

是看 builder 完整输入→输出的好起点。

## 相关链接

- [CLI 参考 § chat](cli.md#chat)
- [前端集成](../web-ui/frontend-integration.md) — 嵌入到多租户平台
- [配置指南](configuration.md) — builder 写出的 schema
