# 示例画廊

LLM4AD 在 `examples/applications/` 下提供了 17 个可直接运行的示例项目。每个示例都有自己的 `config.yaml`、评估器和算法模板 — 选一个最接近你问题的，复制后改造即可。

下面的实战走读聚焦几个最有代表性的样例。完整表格列出了所有内置示例及其源码链接。

## 精选实战

| 示例 | 领域 | 编排器 | 亮点 |
|---|---|---|---|
| [排序基准](sorting.md) | 算法工程 | Island GA | 单目标，最快上手的端到端运行 |
| [TSP 基准](tsp.md) | 组合优化 | Island GA / DyCA / MEoH | 在同一任务上对比三种编排器 |
| [LunarLander（RL）](lunarlander.md) | 强化学习 | Island GA / DyCA | OpenAI Gym 中的策略搜索，含多模态变体 |
| [符号回归](symbolic-regression.md) | 科学发现 | Island GA | 双层评估，预定义常量 |
| [ML 超参数搜索](ml-hyperpara.md) | AutoML | Island GA | 时间预算下进化调优函数 |

## 完整示例清单

源码根：[`examples/applications/`](https://github.com/Optima-CityU/LLM4AD_Next/tree/main/examples/applications)。

| 示例 | 路径 | 多模态 | 说明 |
|---|---|---|---|
| sorting_benchmark | `examples/applications/sorting_benchmark/` | — | 可执行文件评估器（C++ 构建） |
| sorting_benchmark_python | `examples/applications/sorting_benchmark_python/` | — | 纯 Python；详见[排序](sorting.md) |
| tsp_benchmark_python | `examples/applications/tsp_benchmark_python/` | — | 详见 [TSP](tsp.md)；自带 Island GA、DyCA、MEoH 三套配置 |
| tsp_benchmark_python_mock | `examples/applications/tsp_benchmark_python_mock/` | — | 同任务 + `MockProvider`，适合测试/CI |
| tsp_benchmark_python_multimodal | `examples/applications/tsp_benchmark_python_multimodal/` | ✓ | 把巡回路径可视化注入提示词 |
| lunarlander_python | `examples/applications/lunarlander_python/` | — | 详见 [LunarLander](lunarlander.md)；含 `lunarlander_dyca_config.yaml` |
| lunarlander_python_multimodal | `examples/applications/lunarlander_python_multimodal/` | ✓ | 轨迹画面参与变异决策 |
| ml_feature_benchmark | `examples/applications/ml_feature_benchmark/` | — | 特征选择任务 |
| ml_hyperpara_benchmark | `examples/applications/ml_hyperpara_benchmark/` | — | 详见 [ML 超参数搜索](ml-hyperpara.md) |
| symbolic_regression_bilevel_predefined_constant | `examples/applications/symbolic_regression_bilevel_predefined_constant/` | — | 详见[符号回归](symbolic-regression.md) |
| relationship_prediction | `examples/applications/relationship_prediction/` | — | 多实例 LLM-judge 评估器 |
| life_planning | `examples/applications/life_planning/` | — | 长文本规划，LLM-judge 评估 |
| MCM_ICM_problem_2024_D | `examples/applications/MCM_ICM_problem_2024_D/` | — | 数学建模竞赛风格问题 |
| task_template_python | `examples/applications/task_template_python/` | — | 从零开始时的最小脚手架 |
| task_template_python_multimodal | `examples/applications/task_template_python_multimodal/` | ✓ | 多模态脚手架 |

自动生成示例（`llm4ad chat` 产出，置于 [`examples/auto_applications/`](https://github.com/Optima-CityU/LLM4AD_Next/tree/main/examples/auto_applications)）端到端演示了[自动构建](../guides/auto-builder.md)流程。

## 运行任意示例

```bash
cd LLM4AD
uv sync
export LLM_API_KEY="sk-..."
export LLM_BASE_URL="https://api.openai.com/v1"   # 可选
export LLM_MODEL="gpt-4o-mini"

llm4ad run examples/applications/sorting_benchmark_python/config.yaml
```

运行目录落在 `./runs/<project_name>/<run_id>/` 下，CLI 在结束时会打印 `best/` 快照路径。

## 相关链接

- [快速开始](../guides/quickstart.md) — 最小端到端运行
- [配置指南](../guides/configuration.md) — 每个 YAML 字段的说明