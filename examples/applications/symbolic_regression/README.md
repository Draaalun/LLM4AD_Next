# Symbolic Regression with Bi-Level Optimization (LLM + EC)

A symbolic regression framework that combines **Large Language Models (LLM)** for equation structure discovery with **BFGS numerical optimization** for parameter optimizaion, evolved through a multi-island genetic algorithm.

---

## How It Works

Symbolic regression aims to discover a mathematical expression `y = f(x0, x1, ..., xN)` that fits a dataset. This framework splits that hard problem into two layers, each handled by the tool best suited for it.

### The Bi-Level Idea

```
                ┌─────────────────────────────────────────┐
                │  LEVEL 1: Equation Structure (LLM)      │
                │  "What's the SHAPE of the equation?"    │
                │                                         │
                │  Example output:                        │
                │    params[0] * sin(x0) + params[1]*x1   │
                └─────────────────┬───────────────────────┘
                                  │
                                  ▼
                ┌─────────────────────────────────────────┐
                │  LEVEL 2: Parameter Values (BFGS)       │
                │  "What NUMBERS make it fit best?"       │
                │                                         │
                │  Example output:                        │
                │    params = [2.31, -0.85]               │
                └─────────────────┬───────────────────────┘
                                  │
                                  ▼
                ┌─────────────────────────────────────────┐
                │  EVALUATE: Compute MSE on training data │
                │  fitness = -penalized_mse               │
                └─────────────────────────────────────────┘
```

### Why Split It This Way?

| Task | Best Tool | Reason |
|------|-----------|--------|
| Pick which functions to compose (`sin`, `exp`, `**2`...) | **LLM** | Pattern recognition, mathematical intuition, creative composition |
| Tune numerical constants like `2.31` | **BFGS** | Gradient-based, converges in milliseconds, exact |
| Explore the vast space of possible structures | **Evolution (GA)** | Population diversity, mutation/crossover, escape local optima |

Asking the LLM to also guess exact numbers like `2.31415` is wasteful — that's what gradient descent excels at. Asking BFGS to invent the equation form is impossible — that's a discrete combinatorial problem.

### One Generation, Step by Step

For each candidate individual in each island:

1. **LLM proposes a structure** — a Python function body using `params[0], params[1], ...` placeholders
   ```python
   return params[0] * np.sin(x0) + params[1] * np.exp(-x1)
   ```
2. **Evaluator counts parameters** by parsing `params[N]` indices → finds 2 params
3. **BFGS runs 15 random restarts** with different initial values, picking the best fit
4. **Final MSE on original (denormalized) scale** becomes the fitness signal
5. **Penalty** for too many parameters: `score = -mse * (1 + 0.001 * params_count)`

The Island GA then selects, mutates, and crosses over individuals across generations to evolve better structures.

### Why Negative Fitness Scores?

You'll see logs like `Best score: -0.70`. **This is correct behavior**, not a bug.

| Concept | Value |
|---------|-------|
| Score formula | `score = -penalized_mse` |
| Goal | **Maximize** score (i.e., make it less negative, closer to 0) |
| Interpretation | `-0.70` = penalized MSE of `0.70` |

Evolution **maximizes** fitness, but we want to **minimize** MSE — so we negate. A trajectory of `-2.35 → -1.12 → -0.70 → -0.05` means the model is improving.

---

## Quick Start

### 1. Pick a benchmark and generate data

Edit one line in `generate_data.py`:

```python
BENCHMARK = "nguyen5"  # see "Available Benchmarks" table below
```

Run:

```bash
# Data + YAML auto-synchronized
python generate_data.py
llm4ad run config.yaml
```

> **Black-box Guarantee**: The target function expression is **NEVER** leaked to the LLM
> in the YAML configuration. Only variable count and input ranges are provided.
>
> **Auto-sync**: `python generate_data.py` automatically updates *only* the `background`
> and `prompt_template` fields in the YAML. All other configurations (max_generations,
> model, population size, comments, quotes) are **100% preserved** exactly as you left them.
>
> **Feynman Benchmarks**: To list all 100 Feynman physics equations, uncomment in `generate_data.py`:
> ```python
> list_feynman_benchmarks(); return
> ```
> and `prompt_template` fields in the YAML. All other configurations (max_generations,
> model, population size, comments, quotes) are **100% preserved** exactly as you left them.
>
> **Feynman Benchmarks**: To list all 100 Feynman physics equations, uncomment in `generate_data.py`:
> ```python
> list_feynman_benchmarks(); return
> ```

### 2. What Gets Auto-Updated?

When you run `python generate_data.py`:

| YAML Field | Change Type |
|-----------|-------------|
| `background:` | ✅ **Auto-updated** - Variable count + input ranges (no answer leak!) |
| `prompt_template:` | ✅ **Auto-updated** - Function signature, example, naming rule |
| `max_generations` | ❌ **Never touched** - preserved exactly |
| `num_islands` | ❌ **Never touched** - preserved exactly |
| `model` | ❌ **Never touched** - preserved exactly |
| `temperature` | ❌ **Never touched** - preserved exactly |
| `# Comments` | ❌ **Never touched** - all comments preserved |
| `"Quotes"` | ❌ **Never touched** - original quoting preserved |

**YAML format after update (3-variable example):**
```yaml
background: |
  Dataset has 3 input variables. Input ranges: x0 in (-5, 5), x1 in (-5, 5), x2 in (-5, 5).
  Dataset has 3 input variables. Input ranges: x0 in (-5, 5), x1 in (-5, 5), x2 in (-5, 5).

prompt_template: |
  **INPUT VARIABLE NAMING**: The dataset has 3 input variables, named: `x0, x1, x2`
    - Always use zero-indexed naming: `x0`, `x1`, `x2`, ...
    - Use the EXACT variable names shown in the function signature below.

  def equation(x0: np.ndarray, x1: np.ndarray, x2: np.ndarray, params: np.ndarray) -> np.ndarray:
```
```

---

### 3. Available Benchmarks (111 total)

| Benchmark | Vars | Expression | Input Range |
|-----------|------|------------|-------------|
| **1D** | | | |
| `nguyen1` | 1 | `sin(x0) + sin(x0 + x0**2)` | `x0 ∈ [-1, 1]` |
| `nguyen2` | 1 | `log(x0+1) + log(x0**2 + 1)` | `x0 ∈ [0, 2]` |
| `nguyen3` | 1 | `sqrt(x0)` | `x0 ∈ [0, 4]` |
| `keijzer6` | 1 | `exp(-x0)*x0**3*cos(x0)*sin(x0)*(cos(x0)*sin(x0)**2 - 1)` | `x0 ∈ [0, 10]` |
| **2D** | | | |
| `nguyen4` | 2 | `x0**4 - x0**3 + x1**2/2 - x1` | both `∈ [-1, 1]` |
| `nguyen5` | 2 | `sin(x0) + sin(x1**2)` | both `∈ [-10, 10]` |
| `nguyen6` | 2 | `2*sin(x0)*cos(x1)` | both `∈ [-10, 10]` |
| `nguyen7` | 2 | `x0**x1` | `x0 ∈ [0,1]`, `x1 ∈ [0,4]` |
| `nguyen8` | 2 | `(x0 + x1)**(x0 - x1)` | both `∈ [0, 1]` |
| `nguyen9` | 2 | `exp(-(x0-1)**2) / (1.2 + (x1-2.5)**2)` | both `∈ [0.3, 4]` |
| **3D** | | | |
| `test3var` | 3 | `sin(x0) + cos(x1)*x2` | all `∈ [-5, 5]` |
| `pagie3d` | 3 | `1/(1+x0**-4) + 1/(1+x1**-4) + 1/(1+x2**-4)` | all `∈ [-5, 5]` |
| `keijzer15` | 3 | `sqrt(x0) + sqrt(x1)*sqrt(x2)` | all `∈ [0.01, 5]` |
| **4D / 5D** | | | |
| `synth4d` | 4 | `sin(x0) + exp(-x1) + x2**2 - log(1+x3**2)` | all `∈ [-3, 3]` |
| `synth5d` | 5 | `x0*x1 + sin(x2) + exp(abs(x3)) + log(1+x4**2)` | all `∈ [-2, 2]` |
| **Feynman Series (100 physics equations)** | | | |
| `feynman_I.6.2a` | 1 | Gaussian distribution | various |
| `feynman_I.10.7` | 3 | Relativistic mass | various |
| `feynman_I.12.11` | 5 | Lorentz force | various |
| `feynman_II.13.17` | 4 | (current default) | `[1, 5]` |
| **96 more** | 1–9 | Physics equations from the Feynman Lectures | various |

To list all Feynman benchmarks, uncomment in `generate_data.py`:
```python
list_feynman_benchmarks(); return
```

The evaluator auto-detects column count, so it handles **any dimension** — even 6D, 10D, etc.

---

## Using Custom Functions or Your Own Data

### Method A — You know the target equation

Add it to the `BENCHMARKS` registry in `generate_data.py`:

```python
def my_func(x0, x1):
    return x0**2 + math.sin(x0 * x1)

BENCHMARKS["my_func"] = {
    "func": my_func,
    "n_vars": 2,
    "ranges": [(-5, 5), (-5, 5)],
}
```

Then set `BENCHMARK = "my_func"` and run.

### Method B — Black-box data only

Put space-separated files in place (one sample per line, last column = target):

```
data/train/train_100.txt    # x0 [x1 ... xN] target
data/test/test_50.txt
```

Edit `config.yaml` → `background:` to describe the problem. Run `llm4ad run config.yaml` — no changes to Python needed; the evaluator detects column count automatically.

---

## Key Configuration

```yaml
evolution:
  max_generations: 20         # Number of GA generations
  num_islands: 4              # Parallel sub-populations
  island_population_size: 10  # Individuals per island per generation
  mutation_rate: 0.3
  crossover_rate: 0.5
  early_stop_patience: 10
  early_stop_threshold: 1e-8

providers:
  - name: "default"
    model: "gpt-4o-mini"
    temperature: 0.7
```

---

## Output

Each run gets its own directory under `runs/symbolic_regression/<run_id>/`:

| File | Contents |
|------|----------|
| `state/checkpoint_*.json` | Population snapshot at each checkpoint |
| `state/evolution_state.json` | Final aggregated state, all individuals |
| `generated/island_*_gen_*.json` | Each generated individual with code, MSE, parent IDs |
| `worktrees/island_*/model.py` | Source code of each candidate |
| `logs/` | Detailed execution logs |

Inspect `evaluation.metrics` in any individual JSON for `mse`, `rmse`, `mae`, `penalized_mse`, `params_count`.

---

## Safeguards

### Parameter Limit (Hard + Soft)

- **Hard limit**: Max 30 parameters (`params[0]` to `params[29]`). Anything more → score = 0, rejected.
- **Soft penalty**: Each parameter adds `0.1%` to the MSE used for fitness — encourages parsimony without forbidding complexity.
- **Why both**: BFGS diverges with too many free parameters; the soft penalty nudges evolution toward simpler equations among feasible ones.

### NaN/Inf Protection

The evaluator wraps every equation:
- NaN replaced with `1e10`, ±Inf replaced with `±1e10`
- BFGS failure falls back to Nelder-Mead with 15 random restarts
- Loss function returns `1e10` for invalid predictions (not `NaN`, which would crash the optimizer)

The LLM prompt explicitly steers the model away from NaN-prone constructs:
| Avoid | Use instead |
|-------|-------------|
| `np.log(x)` | `np.log(np.abs(x) + 1e-8)` |
| `np.sqrt(x)` | `np.sqrt(np.abs(x) + 1e-8)` |
| `x ** y` | `np.power(np.abs(x) + 1e-8, y)` |
| `np.exp(x)` (large `x`) | `np.exp(np.clip(x, -10, 10))` |
| `1.0 / x` | `1.0 / (x + 1e-8)` |

### Data Normalization

Before BFGS optimization, both inputs and targets are z-score normalized. Predictions are denormalized before final MSE computation, so reported metrics are on the **original scale** of the data.

---

## Tips

1. **Start simple**: try `nguyen1` or `nguyen5` first to validate your setup before tackling Feynman equations.
2. **Increase generations** for hard problems — `max_generations: 50–200`.
3. **Better LLMs find better structures** — `gpt-4o`, `claude-opus`, etc. usually beat `gpt-4o-mini` for non-trivial expressions.
4. **Watch `params_count`** in the metrics — if it's always hitting 30, the soft penalty might need to be raised (`param_penalty * 0.001` → `0.005` in `predefined_evaluator.py`).
5. **Black-box guarantee**: the YAML `background` field intentionally never includes the target formula, so you can safely benchmark on Feynman without leaking answers to the LLM.
