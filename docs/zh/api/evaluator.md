# 评估器 API

`llm4ad.evaluator` 在数据集上执行算法，并返回带分数的指标，驱动整个进化过程。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `BaseEvaluator` | 自定义 Python 评估器的根基类；继承并实现 `evaluate(...)` | `src/llm4ad/evaluator/base.py` |
| `PythonEvaluator` | 直接调用 Python 函数的便捷子类 | `src/llm4ad/evaluator/base.py` |
| `BenchmarkEvaluator` | 多实例聚合（数据集中每个文件一个评估实例） | `src/llm4ad/evaluator/base.py` |
| `LLMJudgeEvaluator` | 用 LLM 作为评分人的评估器，适合无法直接量化的输出 | `src/llm4ad/evaluator/llm_judge.py` |
| `ExecutableEvaluator` | 运行外部命令并以正则匹配 stdout 抽取指标 | `src/llm4ad/evaluator/base.py` |
| `EvaluationDispatcher` | 按 `evaluator.type` + `module:` 分派到具体实现 | `src/llm4ad/evaluator/dispatcher.py` |
| `EvaluationResult` | 标准返回信封：`score`、`metrics`、`metadata`、`success` 等 | `src/llm4ad/evaluator/base.py` |
| `Metric`、`MetricType` | 单个指标定义（名称、方向、权重） | `src/llm4ad/evaluator/base.py` |
| `BehaviorData`、`BehaviorVisualization` | 多模态评估器返回的行为数据载荷 | `src/llm4ad/evaluator/behavior.py` |
| `BaseRenderer` | 把 `behavior_storage="raw"` 中的原始数据渲染成图像 | `src/llm4ad/evaluator/renderer.py` |

## 编写自定义 Python 评估器

```python
# my_eval.py
from llm4ad.evaluator import PythonEvaluator
from llm4ad.evaluator.base import EvaluationResult, Metric, MetricType

class SortEvaluator(PythonEvaluator):
    metrics = [Metric(name="comparisons", type=MetricType.MINIMIZE)]

    async def evaluate(self, algorithm, ctx) -> EvaluationResult:
        # 在 ctx.project_root 上执行算法、收集统计
        n_cmp = run_algorithm_and_count(ctx.project_root, ctx.data_path)
        return EvaluationResult(
            score=-n_cmp,            # 进化总是 maximize score
            metrics={"comparisons": n_cmp},
            success=True,
            duration_ms=42.0,
        )
```

YAML 中：

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

`module` 字段支持两种语法：`pkg.module:ClassName` 或 `path/to/file.py:ClassName`。除了已知字段外，YAML 上的额外键（如 `api_config:`）会通过 `model_extra` 传给评估器构造函数。

## EvalContext

每次 `evaluate(algorithm, ctx)` 调用都会拿到一个 `EvalContext`：

| 字段 | 含义 |
|---|---|
| `project_root` | 当前个体的 git 工作树根（由编码器创建） |
| `data_path` | 由 `DatasetConfig` 解析出的本次实例路径（依模式而定） |
| `timeout` | 软超时，秒 |
| `behavior_storage` | `"rendered"` / `"raw"` / `"none"` — 提示评估器是否应该收集行为数据 |

## 多实例 / 基准式评估

`BenchmarkEvaluator` 会按 `dataset.mode = files | directory | glob` 中的每个数据集文件并行地调用 `evaluate_instance`，再调用 `aggregate(...)` 把分数和指标合并。

```python
class TSPBenchmark(BenchmarkEvaluator):
    metrics = [Metric(name="tour_length", type=MetricType.MINIMIZE)]

    async def evaluate_instance(self, algorithm, ctx, instance_path) -> EvaluationResult:
        ...

    def aggregate(self, results) -> EvaluationResult:
        avg = sum(r.metrics["tour_length"] for r in results) / len(results)
        return EvaluationResult(score=-avg, metrics={"tour_length": avg})
```

## 行为数据 / 多模态

`EvaluationResult.behavior` 让评估器把图像、轨迹或观察值返回给规划器。需要时启用 `multimodal.enabled` 即可让多模态采样器在提示词里使用这些数据 — 详见[多模态](../guides/multimodal.md)。
当 `behavior_storage="raw"` 时，必须注册 `BaseRenderer` 才能后续从原始数据重建图像；具体范例见 `src/llm4ad/evaluator/renderer.py`。

## 相关链接

- [评估器指南](../guides/evaluators.md) — 任务式实操
- [配置指南](../guides/configuration.md#evaluator) — `evaluator:` 配置块
- 源码权威：`src/llm4ad/evaluator/`
