# Evaluator API

`llm4ad.evaluator` runs algorithms against a dataset and returns scored metrics that drive evolution.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `BaseEvaluator` | Root class for custom Python evaluators; subclass and implement `evaluate(...)` | `src/llm4ad/evaluator/base.py` |
| `PythonEvaluator` | Convenience subclass that calls a Python function directly | `src/llm4ad/evaluator/base.py` |
| `BenchmarkEvaluator` | Multi-instance aggregation (one evaluation per dataset file) | `src/llm4ad/evaluator/base.py` |
| `LLMJudgeEvaluator` | LLM-as-a-judge evaluator for outputs you cannot measure directly | `src/llm4ad/evaluator/llm_judge.py` |
| `ExecutableEvaluator` | Runs an external command and extracts metrics from stdout via regex | `src/llm4ad/evaluator/base.py` |
| `EvaluationDispatcher` | Dispatches to the concrete evaluator based on `evaluator.type` + `module:` | `src/llm4ad/evaluator/dispatcher.py` |
| `EvaluationResult` | Standard return envelope: `score`, `metrics`, `metadata`, `success`, … | `src/llm4ad/evaluator/base.py` |
| `Metric`, `MetricType` | Single-metric definition (name, direction, weight) | `src/llm4ad/evaluator/base.py` |
| `BehaviorData`, `BehaviorVisualization` | Behavior-data payload returned by multimodal evaluators | `src/llm4ad/evaluator/behavior.py` |
| `BaseRenderer` | Renders raw behavior data into images when `behavior_storage="raw"` | `src/llm4ad/evaluator/renderer.py` |

## Writing a custom Python evaluator

```python
# my_eval.py
from llm4ad.evaluator import PythonEvaluator
from llm4ad.evaluator.base import EvaluationResult, Metric, MetricType

class SortEvaluator(PythonEvaluator):
    metrics = [Metric(name="comparisons", type=MetricType.MINIMIZE)]

    async def evaluate(self, algorithm, ctx) -> EvaluationResult:
        # Run the algorithm at ctx.project_root and collect stats
        n_cmp = run_algorithm_and_count(ctx.project_root, ctx.data_path)
        return EvaluationResult(
            score=-n_cmp,            # evolution always maximizes score
            metrics={"comparisons": n_cmp},
            success=True,
            duration_ms=42.0,
        )
```

In YAML:

```yaml
evaluator:
  type: custom
  module: my_eval:SortEvaluator
  metrics: ["comparisons"]
  dataset:
    mode: directory
    path: ./data
    recursive: true
```

`module` accepts two forms: `pkg.module:ClassName` or `path/to/file.py:ClassName`. Extra YAML keys beyond the schema (e.g. `api_config:`) flow through `model_extra` into the evaluator constructor.

## EvalContext

Each `evaluate(algorithm, ctx)` call receives an `EvalContext`:

| Field | Meaning |
|---|---|
| `project_root` | Worktree root for this individual (the coder created it) |
| `data_path` | One instance path resolved from `DatasetConfig` (mode-dependent) |
| `timeout` | Soft timeout in seconds |
| `behavior_storage` | `"rendered"` / `"raw"` / `"none"` — hints whether evaluators should capture behavior data |

## Multi-instance / benchmark evaluation

`BenchmarkEvaluator` calls `evaluate_instance` for each dataset file (per `dataset.mode = files | directory | glob`) in parallel, then `aggregate(...)` combines the scores and metrics.

```python
class TSPBenchmark(BenchmarkEvaluator):
    metrics = [Metric(name="tour_length", type=MetricType.MINIMIZE)]

    async def evaluate_instance(self, algorithm, ctx, instance_path) -> EvaluationResult:
        ...

    def aggregate(self, results) -> EvaluationResult:
        avg = sum(r.metrics["tour_length"] for r in results) / len(results)
        return EvaluationResult(score=-avg, metrics={"tour_length": avg})
```

## Behavior data / multimodal

`EvaluationResult.behavior` lets evaluators return images, trajectories, or observations to the planner. Enable `multimodal.enabled` to feed them into prompts via the multimodal samplers — see [Multimodal](../guides/multimodal.md).
When `behavior_storage="raw"`, register a `BaseRenderer` so images can be reconstructed later from the raw data; see `src/llm4ad/evaluator/renderer.py` for a worked example.

## See also

- [Evaluators Guide](../guides/evaluators.md) — task-oriented walkthrough
- [Configuration Guide](../guides/configuration.md#evaluator) — `evaluator:` schema
- Source of truth: `src/llm4ad/evaluator/`
