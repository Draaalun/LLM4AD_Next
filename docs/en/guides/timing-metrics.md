# Timing & Metrics Guide

This guide covers LLM4AD's fine-grained timing capability:

- How to read the different time metrics
- How to enable timing or fold it into the score
- How to surface unified timing fields from a custom evaluator
- How to view per-evaluation, per-candidate, and per-run timing in the results

## Goals

The feature uniformly records and exposes:

- **Total wall-clock time** of a run, a generation, or a candidate
- **LLM communication time** for the planner and coder phases
- **Evaluation time** of an evaluator (setup, run, parse, validate)
- **Candidate core runtime** — the time spent actually executing the candidate's code

Among these:

- `candidate_runtime_ms` is the right time metric to compare alongside the task's primary metric
- `evaluation_total_ms` is the evaluator-side total
- `llm_planning_ms` and `llm_coding_ms` are observational by default and do not feed into score

## Time models

### 1. Unified `ExecutionTiming`

Defined in `src/llm4ad/infra/timing.py`. Fields:

```python
ExecutionTiming(
    wall_time_ms=0.0,
    llm_planning_ms=0.0,
    llm_coding_ms=0.0,
    evaluation_total_ms=0.0,
    candidate_runtime_ms=0.0,
    overhead_ms=0.0,
)
```

Field semantics:

- `wall_time_ms`: wall-clock total for this object
- `llm_planning_ms`: LLM request time during the planner phase
- `llm_coding_ms`: LLM request time during the coder phase
- `evaluation_total_ms`: evaluator end-to-end time
- `candidate_runtime_ms`: time the candidate's core code spent running
- `overhead_ms`: leftover time after subtracting the named sub-phases

### 2. Per-evaluation `EvaluationBreakdown`

Also defined in `src/llm4ad/infra/timing.py`. Fields:

```python
EvaluationBreakdown(
    runtime_ms=0.0,
    setup_ms=0.0,
    parse_ms=0.0,
    validation_ms=0.0,
    total_ms=0.0,
)
```

Semantics:

- `runtime_ms`: subprocess or candidate-algorithm core runtime
- `setup_ms`: data load, input prep, script lookup, etc.
- `parse_ms`: parsing stdout / output structure
- `validation_ms`: validating result legality
- `total_ms`: total evaluator-call duration

## Where the data shows up

### 1. Single evaluation result

`EvaluationResult` (`src/llm4ad/evaluator/base.py`) carries:

- `duration_ms` — kept in sync with `evaluation_total_ms`
- `timing` — an `EvaluationBreakdown`
- `metrics["candidate_runtime_ms"]`
- `metrics["evaluation_total_ms"]`

Backwards compatibility: if an older evaluator only returns `execution_time_ms`, the dispatcher maps it to `candidate_runtime_ms` automatically.

### 2. Per-candidate

`Algorithm` (`src/llm4ad/planner/base.py`) gains:

- `algorithm.timing`

This aggregates:

- planner LLM time
- coder LLM time
- evaluator total time
- candidate core runtime
- candidate's own wall-clock total

### 3. Per-generation and per-run

State tracking (`src/llm4ad/infra/state.py`) adds:

- `candidate_timings`
- `generation_timing`
- `run_timing`

These are exported via `LLM4AD.export_state()` and written into the run output.

## Configuration

The schema is defined in `src/llm4ad/config/schema.py`. Under `evaluator`, a new `timing_metrics` block:

```yaml
evaluator:
  module: "tsp_evaluator.py:PythonTSPEvaluator"
  timeout: 60.0
  parallel: true
  dataset:
    mode: "directory"
    path: "data/small"
    recursive: false
  timing_metrics:
    enabled: true
    include_in_score: false
    score_components:
      - "candidate_runtime_ms"
    aggregation: "sum"
    weights:
      candidate_runtime_ms: 1.0
```

### Fields

#### `enabled`

- Type: `bool` · Default: `true`
- Whether to collect unified time metrics.

#### `include_in_score`

- Type: `bool` · Default: `false`
- Whether to fold a time metric into the final score.

#### `score_components`

- Type: `list[str]` · Default: `["candidate_runtime_ms"]`
- Names of time fields allowed to enter the score. We recommend only `candidate_runtime_ms`.
- Avoid putting `evaluation_total_ms` into score by default — it includes IO, parse, and validation overhead, which doesn't compare cleanly across instances.

#### `aggregation`

- Type: `"sum" | "mean"` · Default: `"sum"`
- How time metrics are aggregated across multiple dataset instances of one candidate before influencing score.

#### `weights`

- Type: `dict[str, float]`
- Weight for each time metric when entering score. The current implementation is "subtract weighted time from the original score".

## Examples

### 1. Collect time only, do not affect score

```yaml
evaluator:
  timing_metrics:
    enabled: true
    include_in_score: false
```

All time information is still returned and exported; ranking logic is unchanged.

### 2. Fold candidate runtime into score

```yaml
evaluator:
  timing_metrics:
    enabled: true
    include_in_score: true
    score_components:
      - "candidate_runtime_ms"
    aggregation: "sum"
    weights:
      candidate_runtime_ms: 0.2
```

`candidate_runtime_ms` becomes a penalty term — larger time, lower final score.

## Dispatcher aggregation behavior

`src/llm4ad/evaluator/dispatcher.py` — `dispatch_batch()` now:

- Calls the evaluator separately for each (algorithm, dataset file) pair.
- Aggregates the multiple `EvaluationResult` objects of a single algorithm into one combined result.

Default aggregation:

- `candidate_runtime_ms`: summed
- `evaluation_total_ms`: summed
- `execution_time_ms`: kept in sync with `candidate_runtime_ms`
- Other continuous metrics: averaged
- `score`: averaged across instances
- `metadata["per_instance_results"]`: keeps each instance's raw result

The orchestrator therefore sees one aggregated result per candidate, no longer just the first dataset instance.

## Wiring it into your custom evaluator

If you write a new evaluator, follow this contract.

### Recommended pattern

1. Record core runtime around the candidate's execution.
2. Record evaluator total time from the start to the end of `evaluate()`.
3. Return the unified fields:
   - `metrics["candidate_runtime_ms"]`
   - `metrics["evaluation_total_ms"]`
   - `duration_ms`
   - `timing=EvaluationBreakdown(...)`

### Template

```python
import time

from llm4ad.evaluator.base import EvaluationResult
from llm4ad.infra.timing import EvaluationBreakdown


async def evaluate(self, cfg):
    start_time = time.time()

    # setup
    setup_end = time.time()

    # run candidate
    run_start = time.time()
    # ... execute candidate code ...
    runtime_ms = (time.time() - run_start) * 1000

    # parse
    parse_start = time.time()
    # ... parse output ...
    parse_ms = (time.time() - parse_start) * 1000

    # validation
    validation_start = time.time()
    # ... validate output ...
    validation_ms = (time.time() - validation_start) * 1000

    total_ms = (time.time() - start_time) * 1000

    return EvaluationResult(
        score=score,
        metrics={
            "candidate_runtime_ms": runtime_ms,
            "evaluation_total_ms": total_ms,
        },
        duration_ms=total_ms,
        timing=EvaluationBreakdown(
            runtime_ms=runtime_ms,
            setup_ms=(setup_end - start_time) * 1000,
            parse_ms=parse_ms,
            validation_ms=validation_ms,
            total_ms=total_ms,
        ),
        success=True,
    )
```

### Backwards compatibility

If your existing examples already return `execution_time_ms`, return both for now:

```python
metrics = {
    "execution_time_ms": runtime_ms,
    "candidate_runtime_ms": runtime_ms,
    "evaluation_total_ms": total_ms,
}
```

Old and new logic both keep working.

## How the TSP example wires it

See [`examples/applications/tsp_benchmark_python/tsp_evaluator.py`](https://github.com/Optima-CityU/LLM4AD_Next/blob/main/examples/applications/tsp_benchmark_python/tsp_evaluator.py). It returns:

- `tour_length`
- `execution_time_ms`
- `candidate_runtime_ms`
- `evaluation_total_ms`
- `valid_tour`

with `execution_time_ms == candidate_runtime_ms` for backwards compatibility, and `evaluation_total_ms` covering the entire evaluator call.

## Provider and Coder timing

### Provider

`src/llm4ad/infra/provider/base.py` — `GenerationResult` now carries:

- `latency_ms`
- `request_stage`
- `timing`

`request_stage="planner"` routes the time into `llm_planning_ms`; `request_stage="coder"` routes it into `llm_coding_ms`.

### Coder

`src/llm4ad/coder/base.py` — `GenerateResult` now carries `timing`. After the planner has the implemented code, it folds the coder phase back into `Algorithm.timing`.

## Viewing the results

### 1. Per evaluation

The evaluator's `EvaluationResult`:

- `result.metrics["candidate_runtime_ms"]`
- `result.metrics["evaluation_total_ms"]`
- `result.timing`

### 2. Per candidate

In the generated candidate JSON:

- `timing`
- `evaluation`
- `custom_metadata["evaluation_result"]`

### 3. Per run

In the exported state at end of run:

- `candidate_timings`
- `generation_timing`
- `run_timing`
- `module_timing`

## Recommendations

Default strategy:

- Collect every time metric.
- Do not fold time into score by default.
- If you need a time penalty, prefer `candidate_runtime_ms` only.

These should generally **not** become optimization targets:

- `evaluation_total_ms`
- `llm_planning_ms`
- `llm_coding_ms`

…because they are dominated by network, IO, model-side queueing, parsing, and framework overhead.

## Related files

- `src/llm4ad/infra/timing.py`
- `src/llm4ad/config/schema.py`
- `src/llm4ad/evaluator/base.py`
- `src/llm4ad/evaluator/dispatcher.py`
- `src/llm4ad/infra/state.py`
- `src/llm4ad/planner/base.py`
- [`examples/applications/tsp_benchmark_python/tsp_evaluator.py`](https://github.com/Optima-CityU/LLM4AD_Next/blob/main/examples/applications/tsp_benchmark_python/tsp_evaluator.py)
