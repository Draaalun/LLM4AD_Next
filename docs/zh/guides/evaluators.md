# 编写评估函数

本指南解释如何为 LLM4AD 创建自定义评估器。

## 概述

评估器负责通过在测试用例上运行算法并基于指标计算分数来衡量算法质量。LLM4AD 提供了三个基础评估器类：

- **`PythonEvaluator`**: 用于直接评估 Python 代码
- **`ExecutableEvaluator`**: 用于评估编译的可执行文件
- **`BenchmarkEvaluator`**: 用于标准基准测试数据集

## 创建 Python 评估器

### 基本结构

通过扩展 `PythonEvaluator` 创建 Python 评估器：

```python
from llm4ad.evaluator.base import (
    PythonEvaluator,
    EvaluationResult,
    Metric,
    MetricType
)
from llm4ad.config.schema import EvalContext


class MyEvaluator(PythonEvaluator):
    """我的算法的自定义评估器。"""

    def __init__(self, config: EvalContext):
        """初始化评估器。

        Args:
            config: 评估配置
        """
        super().__init__(config)
        # 在此处添加任何自定义初始化

    @property
    def name(self) -> str:
        """返回评估器名称。"""
        return "my_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """定义此评估器计算的指标。"""
        return [
            Metric(
                name="accuracy",
                type=MetricType.MAXIMIZE,
                description="正确结果的比例",
                weight=1.0
            ),
            Metric(
                name="runtime",
                type=MetricType.MINIMIZE,
                description="平均执行时间（秒）",
                weight=0.5
            ),
        ]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """评估算法。

        Args:
            cfg: 包含算法代码的评估配置

        Returns:
            带有分数和指标的 EvaluationResult
        """
        # 您的评估逻辑在这里
        pass
```

### 示例：排序算法评估器

以下是评估排序算法的完整示例：

```python
"""排序算法评估器。"""

import time
from typing import Any

from llm4ad.evaluator.base import (
    PythonEvaluator,
    EvaluationResult,
    Metric,
    MetricType
)
from llm4ad.config.schema import EvalContext


class SortingEvaluator(PythonEvaluator):
    """评估排序算法。"""

    def __init__(self, config: EvalContext):
        super().__init__(config)

    @property
    def name(self) -> str:
        return "sorting_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return [
            Metric(
                name="correctness",
                type=MetricType.MAXIMIZE,
                description="正确排序数组的比例",
                weight=1.0
            ),
            Metric(
                name="avg_time",
                type=MetricType.MINIMIZE,
                description="平均排序时间（秒）",
                weight=0.3
            ),
            Metric(
                name="stability",
                type=MetricType.MAXIMIZE,
                description="排序的稳定性（1.0 = 稳定）",
                weight=0.2
            ),
        ]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """评估排序算法。"""
        # 带有预期结果的测试用例
        test_cases = [
            ([3, 1, 4, 1, 5], [1, 1, 3, 4, 5]),
            ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]),
            ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),
            ([42] * 10, [42] * 10),
            ([], []),
        ]

        total_time = 0.0
        correct = 0
        stable = 0

        for arr, expected in test_cases:
            arr_copy = arr.copy()

            try:
                # 执行排序函数
                start = time.time()

                # 算法代码在 cfg.project_root 中
                # 我们期望它定义一个 'sort' 函数
                exec_globals = {"array": arr_copy}
                exec(cfg.project_root + "\nresult = sort(array)", exec_globals)
                sorted_arr = exec_globals["result"]

                elapsed = time.time() - start
                total_time += elapsed

                # 检查正确性
                if sorted_arr == expected:
                    correct += 1

                    # 检查稳定性（保留相等元素的顺序）
                    if self._is_stable(arr, sorted_arr):
                        stable += 1

            except Exception as e:
                # 执行失败 - 计为不正确
                total_time += 1.0  # 惩罚

        # 计算指标
        num_tests = len(test_cases)
        correctness = correct / num_tests
        avg_time = total_time / num_tests
        stability_score = stable / num_tests

        # 计算总分
        # 越高越好：correctness * 100 - time_penalty
        score = correctness * 100 - avg_time * 10 + stability_score * 5

        return EvaluationResult(
            score=score,
            metrics={
                "correctness": correctness,
                "avg_time": avg_time,
                "stability": stability_score,
            },
            monitor_metrics={
                "correctness": correctness,
                "avg_time": avg_time,
            },
            metadata={
                "num_tests": num_tests,
                "num_correct": correct,
                "num_stable": stable,
            },
            success=True,
        )

    def _is_stable(self, original: list, sorted_arr: list) -> bool:
        """检查排序是否稳定。"""
        # 对于相等元素，保留原始顺序
        # 这是一个简化的检查
        return True  # 实现适当的稳定性检查
```

## 创建可执行文件评估器

对于编译语言（C++、Rust、Go），使用 `ExecutableEvaluator`：

```python
from llm4ad.evaluator.base import ExecutableEvaluator
from llm4ad.config.schema import EvalContext


class CppEvaluator(ExecutableEvaluator):
    """评估 C++ 可执行文件。"""

    def __init__(self, config: EvalContext):
        super().__init__(config)

    @property
    def name(self) -> str:
        return "cpp_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return [
            Metric(name="score", type=MetricType.MAXIMIZE),
        ]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """评估 C++ 可执行文件。"""
        import subprocess

        # 编译代码
        compile_cmd = ["g++", "-o", "program", cfg.project_root]
        subprocess.run(compile_cmd, check=True, timeout=30)

        # 运行可执行文件
        run_cmd = ["./program"]
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=cfg.timeout
        )

        # 解析输出
        metrics = self.parse_output(result.stdout, result.stderr)

        return EvaluationResult(
            score=metrics.get("score", 0.0),
            metrics=metrics,
            success=result.returncode == 0,
        )

    def parse_output(self, stdout: str, stderr: str) -> dict[str, float]:
        """从程序输出解析指标。

        程序应输出格式为的指标：
        METRIC_NAME: value
        """
        import re

        metrics = {}
        pattern = re.compile(r"(\w+)\s*:\s*([-+]?\d*\.?\d+)")

        for line in stdout.splitlines():
            match = pattern.search(line)
            if match:
                name, value = match.groups()
                metrics[name.lower()] = float(value)

        return metrics
```

## 创建基准测试评估器

对于具有多个问题实例的标准基准测试：

```python
from llm4ad.evaluator.base import BenchmarkEvaluator
from llm4ad.config.schema import EvalContext


class MyBenchmarkEvaluator(BenchmarkEvaluator):
    """在标准基准测试上评估。"""

    def __init__(self, config: EvalContext):
        super().__init__(config)
        # 加载问题实例
        self._problem_instances = self.load_dataset(config.data_path)

    @property
    def name(self) -> str:
        return "my_benchmark_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        return [
            Metric(name="accuracy", accuracy=MetricType.MAXIMIZE),
            Metric(name="avg_time", type=MetricType.MINIMIZE),
        ]

    def load_dataset(self, dataset_path: str) -> list[Any]:
        """从数据集加载问题实例。

        Args:
            dataset_path: 数据集文件或目录的路径

        Returns:
            问题实例列表
        """
        import json

        with open(dataset_path) as f:
            data = json.load(f)

        return data["problems"]

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """在所有问题实例上评估。"""
        results = []

        for instance in self.problem_instances:
            # 在此实例上评估
            result = await self._evaluate_instance(instance, cfg)
            results.append(result)

        # 聚合所有实例的结果
        return self.aggregate_results(results)

    async def _evaluate_instance(
        self,
        instance: dict,
        cfg: EvalContext
    ) -> EvaluationResult:
        """在单个问题实例上评估。"""
        # 您的实例评估逻辑在这里
        pass
```

## 注册自定义评估器

### 方法 1：使用注册表

在代码中注册您的评估器：

```python
from llm4ad.evaluator.base import BaseEvaluator
from llm4ad.utils.registry import Registry

# 获取评估器注册表
evaluator_registry = Registry("evaluator", BaseEvaluator)

# 注册您的评估器
@evaluator_registry.register("my_custom_evaluator")
class MyCustomEvaluator(PythonEvaluator):
    # ... 实现
    pass
```

### 方法 2：使用配置模块

在配置文件中指定评估器：

```yaml
evaluator:
  module: "my_module:MyCustomEvaluator"
  # ... 其他设置
```

LLM4AD 将自动导入并实例化评估器。

## 使用数据集

### 加载测试数据

从配置访问数据集路径：

```python
async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
    """评估算法。"""
    import json

    # 从 cfg.data_path 加载数据集
    with open(cfg.data_path) as f:
        dataset = json.load(f)

    # 使用数据集进行评估
    test_cases = dataset["test_cases"]
    # ...
```

### 数据集配置模式

在配置文件中配置数据集发现：

```yaml
evaluator:
  dataset:
    mode: "files"  # 或 "directory" 或 "glob"
    files:
      - "./data/test1.json"
      - "./data/test2.json"
```

## 错误处理

在评估器中优雅地处理错误：

```python
async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
    """评估算法。"""
    try:
        # 您的评估逻辑
        result = self._run_evaluation(cfg)
        return result

    except SyntaxError as e:
        # 代码有语法错误
        return EvaluationResult(
            score=0.0,
            metrics={},
            success=False,
            error_message=f"语法错误：{e}",
        )

    except TimeoutError as e:
        # 代码耗时太长
        return EvaluationResult(
            score=0.0,
            metrics={},
            success=False,
            error_message=f"超时：{e}",
        )

    except Exception as e:
        # 其他错误
        return EvaluationResult(
            score=0.0,
            metrics={},
            success=False,
            error_message=f"评估错误：{e}",
            error_message=f"评估错误：{e}",
        )
```

## 最佳实践

### 1. 定义清晰的指标

使用描述性指标名称和类型：

```python
@property
def metrics(self) -> list[Metric]:
    return [
        Metric(
            name="accuracy",
            type=MetricType.MAXIMIZE,
            description="正确预测的比例",
            weight=1.0
        ),
        Metric(
            name="inference_time",
            type=MetricType.MINIMIZE,
            description="平均推理时间（毫秒）",
            weight=0.5
        ),
    ]
```

### 2. 使用超时

使用超时防止无限循环：

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout_context(seconds):
    """超时的上下文管理器。"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"{seconds} 秒后超时")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# 在评估中使用
with timeout_context(30):
    result = self._run_algorithm()
```

### 3. 提供元数据

包含有用的元数据用于调试：

```python
return EvaluationResult(
    score=score,
    metrics=metrics,
    metadata={
        "num_test_cases": len(test_cases),
        "num_passed": passed,
        "num_failed": failed,
        "total_time": total_time,
        "algorithm_hash": self._hash_code(code),
    },
    success=True,
)
```

### 4. 测试您的评估器

为您的评估器编写单元测试：

```python
import pytest
from my_evaluator import SortingEvaluator


def test_sorting_evaluator():
    """测试排序评估器。"""
    config = EvalContext(
        data_path="./test_data.json",
        project_root=".",
        timeout=30.0
    )

    evaluator = SortingEvaluator(config)

    # 测试指标
    assert evaluator.name == "sorting_evaluator"
    assert len(evaluator.metrics) == 3

    # 测试评估
    result = await evaluator.evaluate(config)
    assert result.success
    assert "correctness" in result.metrics
```

## 完整示例

参见[排序示例](../examples/sorting.md)获取完整的工作示例。

## 下一步

- [配置指南](configuration.md) - 配置您的评估器
- [快速入门指南](quickstart.md) - 运行您的第一个实验
- [高级配置](advanced.md) - 高级使用模式
