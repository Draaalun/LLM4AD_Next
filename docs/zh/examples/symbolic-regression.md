# 符号回归（双层优化）

[`examples/applications/symbolic_regression_bilevel_predefined_constant/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/symbolic_regression_bilevel_predefined_constant) 的端到端走读。任务是从含三个输入变量 `x0, x1, x2` 的数值数据中**发现一个数学表达式**，让其均方误差（MSE）最小。

## 关键想法：双层优化

符号回归通常要同时挑选**结构**（哪些项、什么算子）和**常量**（拟合系数）。这个示例把两层职责拆开：

- LLM 提案表达式**结构**，把可调常量写成 `params[0]`、`params[1]`…（最多 30 个）。
- 评估器为每个候选表达式跑一次 BFGS，用梯度下降优化 `params`，再用拟合后的常量评分。

LLM 不需要也几乎做不好"既猜结构又猜常量"。把数值优化交给 BFGS，进化只用来探索结构；这就是配置名里 "bilevel" 的来源。

## 进化对象

EVOLVE 块的目标只是返回一个表达式的函数体：

```python
import numpy as np

# EVOLVE_START
def equation(x0, x1, x2, params):
    return params[0] * np.sin(params[1] * x0) + params[2] * np.exp(-params[3] * x1 ** 2)
# EVOLVE_END
```

这个示例的 `coder.prompt_template` 在惩罚机制上态度强硬：

- 结构必须直接返回 — 禁止建辅助类、解析器或中间变量。
- 每个常量都必须按位置访问（`params[0]`、`params[1]` …）。绝不允许 `a, b = params` 这样的解构。
- 数值上每个参数都会带一点惩罚，鼓励简短表达式。
- 提示词里直接写明 `np.log` / `np.sqrt` / `x ** y` 等需要被裁剪以避免 NaN。

这种约束式提示工程是符号回归走得通的关键。

## 怎么运行

```bash
cd LLM4AD
uv sync
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

# 数据集已用 generate_data.py 预生成
llm4ad run examples/applications/symbolic_regression_bilevel_predefined_constant/config.yaml
```

末尾输出（节选）：

```text
[bold green]Pipeline completed successfully![/bold green] Best score: -0.0042
Best algorithm worktree: sr_algorithm-...
Best snapshot: runs/symbolic_regression_predefined_bilevel/<run_id>/best
```

`score` 是经过参数惩罚的 `-MSE`；越接近 0 越好。

## 评估器走读

`predefined_evaluator.py` 是一个 `BenchmarkEvaluator`，每个数据集文件做一次：

1. 把 `data/<instance>.csv` 加载为 `(x0, x1, x2, y)` 的列。
2. 从 `equation(x0, x1, x2, params)` 中提取 LLM 提议的结构。
3. 通过 `scipy.optimize.minimize(method="BFGS")` 拟合 `params`，把 `np.sum((equation(...) - y) ** 2)` 最小化。
4. 计算最终 MSE 并加上参数惩罚（每个 `params[k]` ≈ 0.1%）。
5. 返回 `EvaluationResult(score=-mse, metrics={"mse": ..., "n_params": ...})`。

`metrics` 同时记录 `mse` 和 `n_params`，便于在 Web UI 里看简洁性 vs 拟合度的折中。

## 看结果

```bash
cat runs/symbolic_regression_predefined_bilevel/<run_id>/best/code/sr_algorithm/equation.py
```

会输出形如：

```python
def equation(x0, x1, x2, params):
    return params[0] * np.sin(params[1] * x0 + params[2]) \
         + params[3] * np.exp(-params[4] * x1 ** 2) \
         + params[5] * x2
```

要在新数据上测试拟合后的表达式：`python sr_algorithm/run_inference.py "..."`。

## 可以试的变体

- **改进展宽**：`max_generations: 30`、`population_size: 8`，提示词里要求 `params[0..15]` 即可，鼓励更短解。
- **多目标 MEoH**：把 `evolution.type` 改 `meoh`，列 `objective_metrics: ["mse", "n_params"]`，会得到 Pareto 前沿（精度 vs 复杂度）。
- **不同输入维度**：用 `generate_data.py` 改 `--n_inputs`，注意更新提示词中的变量列表 (`x0, x1, ...`)。

## 相关链接

- [评估器指南](../guides/evaluators.md) — 理解 BenchmarkEvaluator
- [配置指南](../guides/configuration.md) — `prompt_template`、`metrics`、`evolution`
- [自动构建](../guides/advisor.md) — 用 `llm4ad chat` 由零生成类似项目
