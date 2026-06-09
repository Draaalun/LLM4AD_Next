# ML 超参数搜索

[`examples/applications/ml_hyperpara_benchmark/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/ml_hyperpara_benchmark) 的端到端走读。任务是为一条 ML 流水线进化一个超参数调优函数，在固定算力预算内把基准数据集上的测试准确率最大化。

这个示例展示 LLM4AD 如何超出经典"算法设计"走向 **AutoML 式的搜索**：EVOLVE 块是一个调优函数，不再是排序例程，但流水线（Island GA、评估器、EVOLVE 标记）完全不变。

## 进化对象

EVOLVE 块在 `tuner_algorithm/` 中：

```python
# EVOLVE_START
def tune(model_factory, X_train, y_train, X_val, y_val, time_budget_s):
    """返回 (fitted_model, val_accuracy)。

    内部可以多次调用 model_factory(**hparams)，只要总墙钟时间
    不超过 time_budget_s。
    """
    pass
# EVOLVE_END
```

评估器把它跑在多个 `(model_factory, dataset)` 实例上，聚合验证集准确率。

## 怎么运行

```bash
cd LLM4AD
uv sync --extra eval                  # pandas, numpy, scipy
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

llm4ad run examples/applications/ml_hyperpara_benchmark/config.yaml
```

末尾输出（节选）：

```text
[bold green]Pipeline completed successfully![/bold green] Best score: 0.8753
Best algorithm worktree: tuner_algorithm-...
Best snapshot: runs/ml_hyperpara_benchmark/<run_id>/best
```

`score` 是所有数据集实例的均值验证准确率。

## 评估器走读

评估器把每个实例包到 `BenchmarkEvaluator.evaluate_instance` 里：

1. 从 `data/` 下的 `.npz` 文件加载 `(X_train, y_train, X_val, y_val)`。
2. 加载实例元数据指向的模型工厂（如 scikit-learn 的 `RandomForestClassifier`）。
3. 用严格的 `time_budget_s` 调用候选 `tune(...)`（同时 `evaluator.timeout` 也兜底）。
4. 记录：
   - `val_accuracy` — 主分
   - `time_used_s` — 实际耗时
   - `n_evaluations` — 调优器内部试了多少候选
5. 返回 `EvaluationResult(score=val_accuracy, metrics={...})`。

`aggregate(...)` 报告 `val_accuracy` 的均值和 `time_used_s` 的总和。

## 一个姊妹示例

[`ml_feature_benchmark/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/ml_feature_benchmark) 结构一致，但进化的是**特征选择**例程。当瓶颈来自特征工程而不是超参数时很有用。

## 可以试的变体

- **MEoH 多目标**：列 `objective_metrics: ["val_accuracy", "time_used_s"]`，进化"准确"与"快"的 Pareto 前沿 — 在线上有时间预算时直接可用。
- **不同模型**：把 `RandomForestClassifier` 换成 `GradientBoostingClassifier` 或一个小 MLP，评估器无需改动。
- **真实数据集**：不用 `data/`（由 `generate_data.py` 产出），换成 OpenML 或你自己的 `.npz`。

## 相关链接

- [评估器指南](../guides/evaluators.md) — `BenchmarkEvaluator.aggregate(...)` 机制
- [MEoH](../guides/meoh.md) — 准确率 / 时间折中的 Pareto 前沿
- [配置指南](../guides/configuration.md) — `evaluator.timeout` 与实例级预算
