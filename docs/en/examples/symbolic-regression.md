# Symbolic Regression (Bilevel)

End-to-end walkthrough of [`examples/applications/symbolic_regression_bilevel_predefined_constant/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/symbolic_regression_bilevel_predefined_constant). The task is to **discover a mathematical expression** from numerical data with three inputs `x0, x1, x2`, minimizing mean squared error (MSE).

## Key idea: bilevel optimization

Symbolic regression usually has to select **structure** (which terms, which operators) and **constants** (their fitted values) simultaneously. This example separates the two levels:

- The LLM proposes the expression **structure**, with tunable constants written as `params[0]`, `params[1]`, … (up to 30 of them).
- The evaluator runs BFGS for each candidate expression, gradient-descending the `params` array, then scores the candidate using the fitted constants.

The LLM does not need to (and could rarely) do both "guess the structure" and "guess the values". Hand the numeric optimization to BFGS and use evolution only for structure search; that's the "bilevel" in the project name.

## What evolves

The EVOLVE block is just the body of one function returning the expression:

```python
import numpy as np

# EVOLVE_START
def equation(x0, x1, x2, params):
    return params[0] * np.sin(params[1] * x0) + params[2] * np.exp(-params[3] * x1 ** 2)
# EVOLVE_END
```

The `coder.prompt_template` for this example is a strict, penalty-heavy contract:

- The structure must return directly — no helper classes, parsers, or intermediate variables.
- Every constant must be accessed by index (`params[0]`, `params[1]`, …). No `a, b = params` unpacking.
- A small numerical penalty per parameter encourages short expressions.
- Specific anti-NaN guidance (clip `np.log` / `np.sqrt` / `x ** y`) is baked into the prompt.

This kind of constraint-heavy prompt engineering is what makes symbolic regression tractable here.

## How to run

```bash
cd LLM4AD
uv sync
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

# Dataset is pre-generated under data/ via generate_data.py
llm4ad run examples/applications/symbolic_regression_bilevel_predefined_constant/config.yaml
```

Expected end-of-run output (abridged):

```text
[bold green]Pipeline completed successfully![/bold green] Best score: -0.0042
Best algorithm worktree: sr_algorithm-...
Best snapshot: runs/symbolic_regression_predefined_bilevel/<run_id>/best
```

`score` is `-MSE` plus the parameter-count penalty; closer to 0 is better.

## Evaluator walkthrough

`predefined_evaluator.py` is a `BenchmarkEvaluator` that, for each dataset file:

1. Loads `data/<instance>.csv` into `(x0, x1, x2, y)` columns.
2. Extracts the LLM-proposed structure from `equation(x0, x1, x2, params)`.
3. Fits `params` with `scipy.optimize.minimize(method="BFGS")`, minimizing `np.sum((equation(...) - y) ** 2)`.
4. Computes the final MSE and adds a small per-parameter penalty (~0.1% per `params[k]` referenced).
5. Returns `EvaluationResult(score=-mse, metrics={"mse": ..., "n_params": ...})`.

`metrics` records both `mse` and `n_params` so the Web UI can display the simplicity-vs-fit tradeoff.

## Reading the results

```bash
cat runs/symbolic_regression_predefined_bilevel/<run_id>/best/code/sr_algorithm/equation.py
```

You'll see something like:

```python
def equation(x0, x1, x2, params):
    return params[0] * np.sin(params[1] * x0 + params[2]) \
         + params[3] * np.exp(-params[4] * x1 ** 2) \
         + params[5] * x2
```

To test the fitted expression on new data: `python sr_algorithm/run_inference.py "..."`.

## Variations to try

- **Bigger search**: `max_generations: 30`, `population_size: 8`, and tighten the prompt to allow only `params[0..15]` to encourage shorter solutions.
- **Multi-objective with MEoH**: switch `evolution.type` to `meoh`, list `objective_metrics: ["mse", "n_params"]`, and you'll get a Pareto front trading accuracy against complexity.
- **Different input dimensions**: regenerate `data/` via `generate_data.py` with `--n_inputs`, then update the prompt to mention the right variable list (`x0, x1, ...`).

## See also

- [Evaluators Guide](../guides/evaluators.md) — understanding BenchmarkEvaluator
- [Configuration Guide](../guides/configuration.md) — `prompt_template`, `metrics`, `evolution`
- [Auto Builder](../guides/advisor.md) — start a similar project from scratch via `llm4ad chat`
