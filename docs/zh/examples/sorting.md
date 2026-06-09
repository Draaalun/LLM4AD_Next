# 排序基准

[`examples/applications/sorting_benchmark_python/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/sorting_benchmark_python) 的端到端走读。任务是进化一个 Python 排序函数，让其在一组整数列表测试样例上最小化执行时间和操作数。

## 进化对象

EVOLVE 代码块位于 `version_control:` 声明的 `local_path` 目录 `sorting_algorithm/` 下：

```python
# EVOLVE_START
def your_sort_function(data):
    """原地排序 data，返回 (comparisons, swaps)。"""
    pass
# EVOLVE_END
```

LLM4AD 为每个候选个体创建一个新的 git 工作树，调用 coder 改写这一块，然后用评估器跑 `data/small/` 下的每个实例。

## 怎么运行

```bash
cd LLM4AD
uv sync
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

llm4ad run examples/applications/sorting_benchmark_python/config.yaml
```

末尾输出（节选）：

```text
[bold blue]Running pipeline with config:[/bold blue] examples/applications/sorting_benchmark_python/config.yaml
...
[bold green]Pipeline completed successfully![/bold green] Best score: 0.9842
Best algorithm worktree: sorting_algorithm-abcd1234
Best snapshot: runs/sorting_benchmark_python/<run_id>/best
```

`best/` 目录是末态最佳工作树的稳定副本，外加 `metadata.json` 和 `summary.txt`。可用 `llm4ad evolve check ./runs/<run_id>/best/code` 查看获胜个体的 EVOLVE 块。

## 配置走读

最关键的几段：

```yaml
project_name: "sorting_benchmark_python"
random_seed: 42

providers:
  - name: "default"
    type: "openai_compatible"
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    model: ${LLM_MODEL}

coder:
  type: "custom"            # 朴素 LLM coder，通过 diff 改写 EVOLVE 块
  prompt_template: |        # 多行模板，含 {insight}/{project_context} 占位符
    ...

evaluator:
  type: "custom"
  module: "sorting_evaluator.py:PythonSortingEvaluator"
  dataset:
    mode: "directory"
    path: "data/small"
  metrics: ["execution_time_ms", "comparisons", "swaps"]

evolution:
  type: "island_ga"
  max_generations: 3
  num_islands: 2
  island_population_size: 4

version_control:
  enabled: true
  local_path: "sorting_algorithm"
```

自带的 `config.yaml` 故意把代数压得很小，便于冒烟跑通。真做实验时把 `max_generations` 调到 ~30，`island_population_size` 调到 ~6。

## 评估器走读

`sorting_evaluator.py:PythonSortingEvaluator` 继承自 `BenchmarkEvaluator`。对 `data/small/` 下每个文件：

1. 加载整数列表。
2. 在工作树（`ctx.project_root`）中启动 `python sort.py "<json>"`。
3. 解析 stdout 中的 `{result, comparisons, swaps}`。
4. 记录 `execution_time_ms`。
5. 返回 `EvaluationResult`，`score` 取归一化执行时间的相反数（框架始终最大化 score）。

`metrics` 还列了次要信号（`comparisons`、`swaps`），即使 `score` 是单目标，它们也会在运行摘要里显示。

## 看结果

运行结束后：

```text
runs/sorting_benchmark_python/<run_id>/
├── best/
│   ├── code/                       # 获胜工作树，可直接审阅
│   ├── metadata.json
│   └── summary.txt
├── state/evolution_state.json      # Web UI 快速分析视图读取
├── checkpoints/last.json
├── logs/
└── generated/
```

后续动作：

- `cat runs/.../best/summary.txt` — 分数曲线和指标历史。
- `python runs/.../best/code/sort.py "[5,3,8,1,2]"` — 手动跑一下获胜算法。
- `llm4ad run config.yaml -r runs/.../checkpoints/last.json` — 从上一个检查点续跑。

## 可以试的变体

- **更大数据集**：把 `dataset.path` 换成 `data/large/`（用示例自带脚本生成），更接近真实基准。
- **MEoH 多目标**：把 `evolution.type` 改成 `meoh`，列出 `objective_metrics: ["execution_time_ms", "comparisons"]`，编排器会维护 Pareto 前沿而非单一最佳。
- **自由 coder**：把 `coder.type` 切到 `claude_code` 或 `opencode`，让 agent 越过标记块自由编辑（需安装对应 extra）。

## 相关链接

- [快速开始](../guides/quickstart.md) — 同样流程，更小的配置
- [评估器指南](../guides/evaluators.md) — 写自己的评估器
- [配置指南](../guides/configuration.md) — 所有 YAML 字段
