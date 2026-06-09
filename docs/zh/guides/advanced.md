# 高级配置

本指南涵盖 LLM4AD 的高级使用模式和配置。

## 多目标优化

LLM4AD 支持同时优化多个目标。

### 定义多个指标

在评估器中定义多个指标：

```python
@property
def metrics(self) -> list[Metric]:
    return [
        Metric(
            name="accuracy",
            type=MetricType.MAXIMIZE,
            weight=1.0
        ),
        Metric(
            name="inference_time",
            type=MetricType.MINIMIZE,
            weight=0.5
        ),
        Metric(
            name="memory_usage",
            type=MetricType.MINIMIZE,
            weight=0.3
        ),
    ]
```

### Pareto 前沿分析

LLM4AD 自动计算帕累托最优解：

```yaml
evolution:
  # 启用帕累托前沿跟踪
  track_pareto_front: true
  pareto_epsilon: 0.01  # 支配的容差
```

## 分布式计算

使用 Ray 在多台机器上分布式评估。

### 启用 Ray

```yaml
infra:
  type: "ray"
  ray:
    address: "auto"  # 或 "ray://head-node:10001"
    num_workers: 4
    resources_per_worker:
      cpu: 2
      memory: "4GB"
```

### Ray 集群设置

```bash
# 启动 Ray 头节点
ray start --head --port=6379

# 启动工作节点
ray start --address=head-node:6379

# 使用 Ray 运行 LLM4AD
llm4ad run config.yaml
```

## 自定义选择策略

为进化实现自定义选择策略。

### 创建自定义选择器

```python
from llm4ad.utils.registry import Registry

selector_registry = Registry("selector", BaseSelector)


@selector_registry.register("my_selector")
class MySelector(BaseSelector):
    """自定义选择策略。"""

    def select(
        self,
        population: list[Individual],
        num_parents: int
    ) -> list[Individual]:
        """选择父代进行繁殖。"""
        # 您的选择逻辑在这里
        pass
```

### 使用自定义选择器

```yaml
evolution:
  selection_strategy: "my_selector"
  custom_selector_params:
    param1: value1
    param2: value2
```

## 内存系统

配置内存以存储和检索过去的设计。

### 启用内存

```yaml
memory:
  max_entries: 10000
  similarity_threshold: 0.8
  decay_factor: 0.99

  # 内存检索设置
  retrieval:
    top_k: 5
    min_similarity: 0.7
```

### 提示中的内存

LLM4AD 自动将相关内存注入到提示中：

```python
# 内存自动包含在规划器提示中
prompt = f"""
背景：{background}

相关过去的设计：
{memory_entries}

当前任务：{task}

生成改进的算法...
"""
```

## 检查点和恢复

保存并从检查点恢复。

### 检查点配置

```yaml
evolution:
  checkpoint_interval: 10  # 每 10 代保存
  max_checkpoints: 5    # 保留最后 5 个检查点

  # 检查点格式
  checkpoint_format: "json"  # 或 "pickle", "yaml"
```

### 从检查点恢复

```bash
# 列出可用的检查点
llm4ad list-checkpoints ./runs/my-project/

# 从特定检查点恢复
llm4ad resume ./runs/my-project/checkpoint_gen_20.json
```

## 版本控制集成

使用 Git 工作树进行隔离的代码生成。

### Git 工作树配置

```yaml
version_control:
  enabled: true
  type: "git_worktree"
  repo_path: "."
  worktree_base: "./worktrees"
  auto_cleanup: true

  # 提交设置
  commit_on_success: true
  commit_message_template: "算法：{algorithm_name}, 分数：{score}"
```

### 分支管理

```bash
# 为实验创建功能分支
git checkout -b experiment-001

# 运行 LLM4AD（创建工作树）
llm4ad run config.yaml

# 将最佳算法合并回来
git checkout main
git merge experiment-001
```

## 监控和日志记录

配置监控用于生产使用。

### Prometheus 指标

```yaml
monitoring:
  type: "prometheus"
  prometheus:
    enabled: true
    port: 9090
    metrics:
      - "generation_time"
      - "evaluation_time"
      - "population_score"
      - "convergence_rate"
```

### 结构化日志

```yaml
logging:
  level: "INFO"
  format: "json"  # JSON 格式用于日志聚合
  file: "./logs/experiment.jsonl"
  console: false

  # 日志轮换
  rotation:
    max_size: "100MB"
    backup_count: 10
```

## 超参数调优

使用 LLM4AD 进行超参数优化。

### 网格搜索

```python
import itertools

# 定义参数网格
param_grid = {
    "temperature": [0.3, 0.5, 0.7],
    "population_size": [20, 50, 100],
    "mutation_rate": [0.2, 0.3, 0.4],
}

# 生成所有组合
for params in itertools.product(*param_grid.values()):
    config = load_base_config()
    config.providers[0].temperature = params[0]
    config.evolution.population_size = params[1]
    config.evolution.mutation_rate = params[2]

    # 运行实验
    run_experiment(config)
```

### 贝叶斯优化

```python
from optuna import create_study

def objective(trial):
    config = load_base_config()

    # 建议参数
    config.providers[0].temperature = trial.suggest_float("temp", 0.1, 1.0)
    config.evolution.population_size = trial.suggest_int("pop_size", 10, 100)
    config.evolution.mutation_rate = trial.suggest_float("mut_rate", 0.1, 0.5)

    # 运行实验并返回分数
    result = run_experiment(config)
    return result.best_score

# 运行优化
study = create_study(direction="maximize")
study.optimize(objective, n_trials=50)
```

## 自定义编码器策略

实现自定义代码生成策略。

### 目标进化

```yaml
coder:
  type: "custom"
  strategy: "targeted_evolution"

  # 目标特定代码块
  targets:
    - "EVOLVE: main_loop"
    - "EVOLVE: optimization"

  # 进化参数
  evolution_params:
    insertion_rate: 0.2
    deletion_rate: 0.1
    replacement_rate: 0.3
```

### 多文件生成

```python
class MultiFileCoder(BaseCoder):
    """生成多个文件。"""

    async def generate(self, prompt: str) -> dict[str, str]:
        """生成多个代码文件。"""
        files = {}

        # 生成主文件
        files["main.py"] = await self._generate_main(prompt)

        # 生成辅助文件
        files["utils.py"] = await self._generate_utils(prompt)
        files["config.py"] = await self._generate_config(prompt)

        return files
```

## 性能优化

### 并行评估

```yaml
evaluator:
  parallel: true
  batch_size: 10  # 并行评估 10 个实例

  # 进程池设置
  max_workers: 8
  chunk_size: 5
```

### 缓存

```yaml
cache:
  enabled: true
  cache_dir: "./cache"
  max_size: "1GB"

  # 缓存键
  cache_by: "code_hash"  # 或 "prompt_hash", "full_hash"
```

### 资源限制

```yaml
resources:
  max_memory: "16GB"
  max_cpu: 8
  max_gpu: 1

  # 每代超时
  generation_timeout: 300
  evaluation_timeout: 60
```

## 最佳实践

1. **从小开始**：从简单配置开始
2. **监控资源**：跟踪 CPU、内存和 API 使用
3. **使用检查点**：为长时间运行启用检查点
4. **调整参数**：为您的问题调整进化参数
5. **版本控制**：使用 Git 工作树进行干净的代码管理
6. **分发工作**：使用 Ray 进行大规模实验
7. **记录所有内容**：启用结构化日志用于分析

## 下一步

- [配置指南](configuration.md) - 基本配置
- [编写评估函数](evaluators.md) - 创建自定义评估器
- [快速入门指南](quickstart.md) - 运行您的第一个实验
