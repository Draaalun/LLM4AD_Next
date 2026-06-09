# TSP 基准

[`examples/applications/tsp_benchmark_python/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/tsp_benchmark_python) 的端到端走读。任务是进化一个 TSP 求解器（最近邻 + 局部搜索风格），让它在涵盖小型随机、聚集型布局和大型随机三类实例的多样化数据集上把巡回距离最小化。

这是仓库里**唯一**自带三套不同编排器配置的示例 — 同任务直接对比 Island GA、DyCA 和 MEoH 一目了然。

## 进化对象

EVOLVE 代码块在 `tsp_algorithm/` 中：

```python
# EVOLVE_START
def nearest_neighbor_tsp(nodes):
    """求解 TSP，返回节点索引序列。"""
    pass
# EVOLVE_END
```

evaluator 把每个数据集实例（一组 (x,y) 坐标）传给该函数，验证巡回路径有效性，并测量总欧氏距离。

## 配置矩阵

```text
examples/applications/tsp_benchmark_python/
├── config.yaml                          # 默认 Island GA
├── tsp_dyca_config.yaml                 # DyCA：按实例聚类、专家池
├── tsp_benchmark_meoh_config.yaml       # MEoH：tour_length 与 execution_time_ms 的多目标
└── tsp_benchmark_meoh_debug_config.yaml # MEoH 紧促轻量调试
```

| 配置 | type | 优势 | 何时选 |
|---|---|---|---|
| `config.yaml` | island_ga | 简单可解释，并行 | 想要单个赢家 |
| `tsp_dyca_config.yaml` | dyca | 按实例聚类的专家算法 | 数据集天然是异质的（小/聚集/大） |
| `tsp_benchmark_meoh_config.yaml` | meoh | 速度/质量的 Pareto 前沿 | 需要多个折中算法 |

## 怎么运行

```bash
cd LLM4AD
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

# 1) Island GA（默认，最快）
llm4ad run examples/applications/tsp_benchmark_python/config.yaml

# 2) DyCA — 实例聚类
llm4ad run examples/applications/tsp_benchmark_python/tsp_dyca_config.yaml

# 3) MEoH — 多目标 Pareto 前沿
llm4ad run examples/applications/tsp_benchmark_python/tsp_benchmark_meoh_config.yaml
```

MEoH 配置为多目标，CLI 输出会变成：

```text
[bold green]Pipeline completed successfully![/bold green] Best objectives: [tour_length=482.15, execution_time_ms=12.30]
Elitist archive: 6 non-dominated solutions
  - meoh_e2_op_3: [tour_length=482.15, execution_time_ms=12.30]
  - meoh_m1_op_7: [tour_length=494.87, execution_time_ms=4.10]
  ...
Best snapshot: runs/tsp_benchmark_python/<run_id>/best
```

每个非支配解都被导出到 `best/pareto/<idx>/`。

## 数据集结构

`data/diverse/` 通过 `generate_diverse_data.py` 创建。每个文件是一组节点：

```json
{"nodes": [[0.12, 0.84], [0.31, 0.55], [0.91, 0.07], ...]}
```

evaluator（`tsp_evaluator.py:PythonTSPEvaluator`）按 `dataset.mode: directory` 并行处理整个目录，并在 `aggregate(...)` 里求平均 `tour_length`。

## 编排器对比

```mermaid
flowchart LR
    Same[同一问题<br/>同一数据集<br/>同一 LLM] --> IGA[Island GA<br/>config.yaml]
    Same --> DYC[DyCA<br/>tsp_dyca_config.yaml]
    Same --> MEH[MEoH<br/>tsp_benchmark_meoh_config.yaml]
    IGA --> R1[1 个全局最佳]
    DYC --> R2[每聚类的专家算法<br/>+ 1 个通才]
    MEH --> R3[(tour_length, time) 上的<br/>Pareto 存档]
```

跑完三个编排器后，对比 `runs/tsp_benchmark_python/<run_id>/best/summary.txt` 的趋势。这是体感 LLM4AD 编排策略选择的最快方法。

## 看结果

```bash
# 每个非支配解（仅 MEoH）：
ls runs/tsp_benchmark_python/<run_id>/best/pareto/
# 每个目录都装着一份完整的工作树，能跑

# 把获胜的最近邻替代品在新实例上手动跑一遍：
cd runs/tsp_benchmark_python/<run_id>/best/code
python tsp_solver.py "$(cat new_instance.json)"
```

## 可以试的变体

- **混合编码器**：同一个配置里 `coder.type: claude_code`、`planner.provider: default`、`coder.provider: stronger_model`，把规划交给便宜模型，把编码交给更强的。
- **更大数据集**：用 `generate_tsp100_data.py` 生成 100 城实例，把 `evaluator.timeout` 提到 300。
- **多模态变体**：把 `tsp_benchmark_python_multimodal/config.yaml` 当作模板 — 它把巡回路径渲染成图，注入提示词。

## 相关链接

- [DyCA](../guides/dyca.md) · [MEoH](../guides/meoh.md) · [Island GA](../guides/island-ga.md)
- [编排方法概览](../guides/orchestration.md) — 选哪个编排器
- [配置指南](../guides/configuration.md) — 所有 YAML 字段
