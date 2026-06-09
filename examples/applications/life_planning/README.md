# Life Planning Example (v4 — LLMJudgeEvaluator)

This example demonstrates how to use LLM4AD to evolve **prompt engineering strategies** for an LLM-based life plan generator. The framework evolves Python scripts that call an LLM API to produce personalized, structured life plans in Markdown format.

## What Changed in v4

This version uses the new `LLMJudgeEvaluator` base class from `src/llm4ad/evaluator/llm_judge.py`, which encapsulates the common "execute script → LLM judge → parse scores" pattern. 
- **`metrics`** — what dimensions to score and their weights
- **`build_judge_prompt()`** — the scoring rubric for the LLM judge

All generic logic (script discovery, subprocess execution, data conversion, LLM API calls, JSON parsing, error handling) is inherited from the base class.

## Overview

This example includes:

- **`config.yaml`**: Complete LLM4AD configuration for the evolutionary pipeline
- **`life_evaluator.py`**: Custom evaluator extending `LLMJudgeEvaluator` (judge prompt + metrics only)
- **`data/`**: User profile datasets (YAML) representing different personas
- **`workspace/`**: Git repository with seed script containing EVOLVE blocks
- **`export_best.py`**: Script to export the best-scoring life plan to Markdown (with language selection)

## Prerequisites

- Python 3.10+
- LLM4AD installed (`uv sync` or `pip install -e .`)
- An OpenAI-compatible API key (e.g., DeepSeek, Kimi, OpenAI)

## Setup

1. Install LLM4AD dependencies:

```bash
uv sync
```

2. Configure your LLM provider in `config.yaml`:

```yaml
providers:
  - name: "planner_llm"
    type: "openai_compatible"
    base_url: "https://your-api-endpoint"
    api_key: "your-api-key"
    model: "your-model-name"

evaluator:
  api_config:
    base_url: "https://your-api-endpoint"
    api_key: "your-api-key"
    model: "your-model-name"
```

## Running the Evolutionary Pipeline

```bash
llm4ad run examples/applications/life_planning/config.yaml
```

## How It Works

1. **Problem Definition**: Evolve a prompt engineering strategy that produces high-quality, personalized life plans
2. **EVOLVE Block**: The `workspace/plan.py` contains an EVOLVE block wrapping the `build_prompt()` function. This function constructs the prompt sent to the LLM API. Evolution optimizes this prompt strategy.
3. **Code Generation**:
   - `init_sampler` analyzes the EVOLVE block and generates improvement insights
   - The coder modifies only the EVOLVE block based on each insight
   - Subsequent generations build on the best strategies via selection and mutation
4. **Evaluation** (per profile):
   - `LLMJudgeEvaluator` runs the script, which calls the LLM API to generate a plan
   - An LLM judge scores the output on four dimensions:
     - **Actionability** (weight: 0.30): Are goals S.M.A.R.T and concrete?
     - **Alignment** (weight: 0.30): Does the plan reflect the user's values and aspirations?
     - **Comprehensiveness** (weight: 0.15): Does the plan cover all key life areas?
     - **Personalization** (weight: 0.25): Are goals genuinely derived from this specific user's profile?
   - Scores range from 1-10, weighted average becomes the fitness score
5. **Evolution**: Island GA evolves better prompt strategies over generations

## Creating a New Task with LLMJudgeEvaluator

To adapt this pattern for a different LLM-judged task:

```python
from llm4ad.evaluator.base import Metric, MetricType
from llm4ad.evaluator.llm_judge import LLMJudgeEvaluator


@LLMJudgeEvaluator.register("my_evaluator")
class MyEvaluator(LLMJudgeEvaluator):

    @property
    def name(self) -> str:
        """Get evaluator name."""
        return "my_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Define scoring dimensions and weights."""
        return [
            Metric(name="quality", type=MetricType.MAXIMIZE, weight=0.5),
            Metric(name="creativity", type=MetricType.MAXIMIZE, weight=0.5),
        ]

    def build_judge_prompt(self, data_content: str, script_output: str) -> str:
        """Build the LLM judge scoring rubric."""
        return f"""Score this output on quality (1-10) and creativity (1-10).
Input data: {data_content}
Output: {script_output}
Return JSON: {{"quality": N, "creativity": N}}"""
```

Optional overrides:
- `script_patterns` — filenames to search for (default: `["implementation.py", "plan.py"]`)
- `script_timeout` — subprocess timeout in seconds (default: 300)
- `prepare_data()` — custom data format conversion
- `parse_judge_response()` — custom JSON parsing

## Exporting Results

After a run completes, export the best life plan:

```bash
# Output as-is (no translation)
python examples/applications/life_planning/export_best.py

# Translate to English
python examples/applications/life_planning/export_best.py --lang en

# Translate to Chinese
python examples/applications/life_planning/export_best.py --lang zh
```

## Adding New Profiles

Add a YAML file to `data/` with this structure:

```yaml
name: "Alice"
age: 28
current_role: "Data Scientist"
aspirations:
  - "Transition to ML engineering lead"
  - "Run a half marathon"
values:
  - "Impact-driven work"
  - "Physical health"
time_horizon_years: 5
```

## Project Structure

```
life_planning/
├── README.md                   # This file
├── config.yaml          # LLM4AD pipeline configuration
├── life_evaluator.py           # Custom evaluator (extends LLMJudgeEvaluator)
├── export_best.py              # Export best plan with language selection
├── data/                       # User profile datasets
├── workspace/                  # Git repo template for worktrees
│   └── plan.py                 # Seed script with EVOLVE block
└── result/                     # Output directory
```

## Model Recommendations


**Tip**: Reasoning models consume tokens for internal "thinking", often causing code truncation. Non-reasoning models are strongly recommended.

## License

This example is part of the LLM4AD project.