# 细粒度计时与计时打分指南

本指南介绍 LLM4AD 中新增的通用细粒度计时能力，包括：

- 如何理解不同时间指标的语义
- 如何在配置中启用或将时间纳入 score
- 如何在自定义 evaluator 中接入统一计时字段
- 如何在运行结果中查看单次评测、候选体和整轮实验的时间信息

## 目标

该功能用于统一记录和暴露以下几类时间：

- **总运行时间**：一次 run、一个 generation、一个 candidate 的墙钟时间
- **LLM 通讯时间**：planner 和 coder 与模型服务交互的耗时
- **任务评估时间**：evaluator 总耗时，包含准备、执行、解析、校验
- **候选核心代码运行时间**：evaluator 实际执行候选算法代码的耗时

其中：

- `candidate_runtime_ms` 是最适合和任务原始指标一起分析的时间指标
- `evaluation_total_ms` 是 evaluator 端整体开销
- `llm_planning_ms` 和 `llm_coding_ms` 默认只做观测，不参与 score

## 时间模型

### 1. 统一执行时间模型 `ExecutionTiming`

定义位置：

- `src/llm4ad/infra/timing.py`

字段说明：

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

字段语义：

- `wall_time_ms`：当前对象的总墙钟时间
- `llm_planning_ms`：planner 阶段的 LLM 请求时间
- `llm_coding_ms`：coder 阶段的 LLM 请求时间
- `evaluation_total_ms`：evaluator 整体耗时
- `candidate_runtime_ms`：候选核心代码运行耗时
- `overhead_ms`：总时间减去主要子阶段后的剩余开销

### 2. 单次评测时间模型 `EvaluationBreakdown`

同样定义在：

- `src/llm4ad/infra/timing.py`

字段说明：

```python
EvaluationBreakdown(
    runtime_ms=0.0,
    setup_ms=0.0,
    parse_ms=0.0,
    validation_ms=0.0,
    total_ms=0.0,
)
```

字段语义：

- `runtime_ms`：子进程或候选算法本体运行时间
- `setup_ms`：加载数据、准备输入、定位脚本等前置阶段时间
- `parse_ms`：解析 stdout / 输出结构的时间
- `validation_ms`：校验结果合法性的时间
- `total_ms`：整个 evaluator 调用总时间

## 数据会出现在哪些层级

### 1. 单次评测结果

`EvaluationResult` 已扩展，定义位置：

- `src/llm4ad/evaluator/base.py`

新增和约定字段：

- `duration_ms`
  - 与 `evaluation_total_ms` 保持一致
- `timing`
  - 存放 `EvaluationBreakdown`
- `metrics["candidate_runtime_ms"]`
- `metrics["evaluation_total_ms"]`

兼容字段：

- 如果旧 evaluator 仍然只返回 `execution_time_ms`，dispatcher 会自动映射到 `candidate_runtime_ms`

### 2. 单个候选算法

`Algorithm` 已扩展，定义位置：

- `src/llm4ad/planner/base.py`

新增字段：

- `algorithm.timing`

这个字段会聚合：

- planner 的 LLM 时间
- coder 的 LLM 时间
- evaluator 总时间
- candidate 核心运行时间
- candidate 自身总墙钟时间

### 3. generation 与 run 汇总

状态追踪定义位置：

- `src/llm4ad/infra/state.py`

新增输出：

- `candidate_timings`
- `generation_timing`
- `run_timing`

这些内容可以通过 `LLM4AD.export_state()` 导出，并被写入运行结果。

## 配置方法

配置定义位置：

- `src/llm4ad/config/schema.py`

在 `evaluator` 下新增了 `timing_metrics`：

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

### 字段说明

#### `enabled`

- 类型：`bool`
- 默认值：`true`

是否启用统一时间指标收集。

#### `include_in_score`

- 类型：`bool`
- 默认值：`false`

是否把指定时间指标并入最终 score。

#### `score_components`

- 类型：`list[str]`
- 默认值：`["candidate_runtime_ms"]`

允许参与 score 的时间字段名。建议优先只使用：

- `candidate_runtime_ms`

不建议默认把 `evaluation_total_ms` 纳入 score，因为它包含 IO、解析、校验等额外开销，不适合跨样例比较。

#### `aggregation`

- 类型：`"sum" | "mean"`
- 默认值：`"sum"`

当一个 candidate 对多个 dataset 实例评测时，时间指标如何聚合后参与 score。

#### `weights`

- 类型：`dict[str, float]`

时间指标进入 score 时的权重。当前实现采用“从原 score 中减去加权时间”的方式。

## 使用示例

### 1. 只收集时间，不影响 score

```yaml
evaluator:
  timing_metrics:
    enabled: true
    include_in_score: false
```

这时：

- 所有时间信息仍会被返回和导出
- 排名逻辑保持原样

### 2. 将候选运行时间并入 score

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

这时：

- `candidate_runtime_ms` 会以惩罚项形式影响最终 score
- 时间越大，最终 score 越低

## Dispatcher 聚合行为

定义位置：

- `src/llm4ad/evaluator/dispatcher.py`

现在 `dispatch_batch()` 的行为是：

- 对每个 algorithm 的每个 dataset file 分别调用 evaluator
- 将同一个 algorithm 的多个 `EvaluationResult` 聚合成一个总结果

聚合后默认行为：

- `candidate_runtime_ms`：求和
- `evaluation_total_ms`：求和
- `execution_time_ms`：与 `candidate_runtime_ms` 同步
- 普通连续指标：默认取平均
- `score`：默认取各实例 `score` 的平均值
- `metadata["per_instance_results"]`：保留每个实例的原始结果

这意味着 orchestrator 现在拿到的是“每个 candidate 的聚合结果”，不再错误地只取第一个数据集结果。

## 在自定义 evaluator 中如何接入

如果你要写新的 evaluator，建议遵守下面的统一约定。

### 推荐做法

1. 在候选代码执行前后单独记录核心运行时间
2. 在 `evaluate()` 开始到结束记录 evaluator 总时间
3. 返回统一字段：
   - `metrics["candidate_runtime_ms"]`
   - `metrics["evaluation_total_ms"]`
   - `duration_ms`
   - `timing=EvaluationBreakdown(...)`

### 推荐模板

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

### 兼容旧字段

如果你的旧样例已经在用 `execution_time_ms`，建议暂时同时返回：

```python
metrics = {
    "execution_time_ms": runtime_ms,
    "candidate_runtime_ms": runtime_ms,
    "evaluation_total_ms": total_ms,
}
```

这样旧逻辑和新逻辑都能兼容。

## TSP 样例中的落地方式

参考文件：

- [`examples/applications/tsp_benchmark_python/tsp_evaluator.py`](https://github.com/Optima-CityU/LLM4AD_Next/blob/main/examples/applications/tsp_benchmark_python/tsp_evaluator.py)

这个样例现在同时返回：

- `tour_length`
- `execution_time_ms`
- `candidate_runtime_ms`
- `evaluation_total_ms`
- `valid_tour`

其中：

- `execution_time_ms` 与 `candidate_runtime_ms` 同值，用于兼容旧代码
- `evaluation_total_ms` 代表整个 evaluator 调用耗时

## Provider 与 Coder 的时间

### Provider

定义位置：

- `src/llm4ad/infra/provider/base.py`

`GenerationResult` 现在包含：

- `latency_ms`
- `request_stage`
- `timing`

其中：

- `request_stage="planner"` 时，时间会进入 `llm_planning_ms`
- `request_stage="coder"` 时，时间会进入 `llm_coding_ms`

### Coder

定义位置：

- `src/llm4ad/coder/base.py`

`GenerateResult` 现在包含：

- `timing`

这使得 planner 在实现代码后，可以把 coder 阶段耗时合并回 `Algorithm.timing`。

## 如何查看结果

### 1. 查看评测结果

样例 evaluator 返回的 `EvaluationResult` 中可直接查看：

- `result.metrics["candidate_runtime_ms"]`
- `result.metrics["evaluation_total_ms"]`
- `result.timing`

### 2. 查看候选体聚合信息

在生成的 candidate JSON 中查看：

- `timing`
- `evaluation`
- `custom_metadata["evaluation_result"]`

### 3. 查看整轮实验状态

运行结束后导出的 state 中查看：

- `candidate_timings`
- `generation_timing`
- `run_timing`
- `module_timing`

## 设计建议

推荐默认策略：

- 记录所有时间
- 默认不把时间并入 score
- 如需引入时间惩罚，优先只使用 `candidate_runtime_ms`

不推荐默认把这些时间直接作为优化目标：

- `evaluation_total_ms`
- `llm_planning_ms`
- `llm_coding_ms`

因为它们受网络、IO、模型端排队、解析和框架开销影响更大。

## 相关文件

- `src/llm4ad/infra/timing.py`
- `src/llm4ad/config/schema.py`
- `src/llm4ad/evaluator/base.py`
- `src/llm4ad/evaluator/dispatcher.py`
- `src/llm4ad/infra/state.py`
- `src/llm4ad/planner/base.py`
- [`examples/applications/tsp_benchmark_python/tsp_evaluator.py`](https://github.com/Optima-CityU/LLM4AD_Next/blob/main/examples/applications/tsp_benchmark_python/tsp_evaluator.py)
