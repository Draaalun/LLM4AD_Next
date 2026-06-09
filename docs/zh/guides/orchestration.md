# 编排方法

在 LLM4AD 中，*编排器*（orchestrator）负责两项决策：

1. **每一步调用哪个 sampler** —— `init`、`mutation`、`crossover`、DyCA 算子 `e1` / `e2` / `m1` / `m2` / `summary`、`meoh_*` 系列，或任一多模态变种；
2. **哪些子代存活**进入下一代。

其余关切——Provider、Coder、Evaluator，以及 sampler 内部的 prompt——在所有编排器之间共享。正是这种切分使得同一份代码无需进一步修改即可在今天运行 Island GA、明天运行多目标 EoH。

平台内置三种编排器，覆盖了已知的"迭代 + LLM"方法。由于分界线恰好是 *sampler 选择 + 存活选择*，引入新方法（带反思的 FunSearch、BO 风格外层循环等）仅需一个类——参见[新增编排器](#新增编排器)。

## 三个内置编排器

| | **Island GA** | **DyCA** | **MEoH** |
|---|---|---|---|
| 搜索结构 | 多岛屿种群，周期性迁移 | 按问题实例聚类划分的单种群 | 单种群配合 Pareto 存档 |
| 父代选择 | 岛内 tournament / roulette / rank | 聚类感知：specialist、generalist、complementary 池 | 多目标 tournament |
| sampler 链 | `init` + `mutation` + `crossover`（+ 多模态） | `init` + `e1` / `e2` / `m1` / `m2` / `summary` / `complementary_cross`（+ 多模态） | `meoh_init` + `meoh_e1` / `meoh_e2` / `meoh_m1` / `meoh_m2` |
| 一代的定义 | 所有岛屿一次遍历 | 一次遍历 + 可选重聚类 | 每次 `survival()` |
| 多目标 | 否（单一 `score`） | 否（按聚类比较） | **是**（基于 `objective_metrics` 的 Pareto 前沿） |
| 推荐场景 | 快速起步、并行探索 | 数据分布异质 | 真正的 Pareto 权衡（质量 vs 速度等） |
| 额外依赖 | 无 | `--extra dyca` | `--extra meoh` |
| 详细页 | [Island GA](island-ga.md) | [DyCA](dyca.md) | [MEoH](meoh.md) |

选择建议：

- **Island GA** —— 单一且充分理解的问题，数据分布大致同质，期望产出一个赢家。配置开销最低。
- **DyCA** —— 数据集在不同子集上呈现显著差异（小规模 vs 大规模 TSP、容易 vs 困难的 ML 基准）；同时需要 specialist 与 generalist 算法。建议调优 `n_clusters`、`n_anchors` 与各池大小。
- **MEoH** —— 存在多个互相竞争且无法归约为单一加权分数的目标（精度 vs 算力、巡回长度 vs 运行时、MSE vs 参数量）；期望产出 Pareto 前沿而非单一赢家。

## 将已发表方法映射到 LLM4AD

LLM4AD 的原子性意味着大多数已发表方法对应于一个特定的 *(编排器, sampler 集, evaluator 类型)* 三元组；选择体现在组件层面，而非"方法标签"。

| 已发表方法 | 编排器 | sampler 链 | Evaluator | 备注 |
|---|---|---|---|---|
| **FunSearch** (Romera-Paredes 等, 2024) | `island_ga` | 仅 `init_sampler` + `mutation_sampler` | 任意 `PythonEvaluator` | 设 `crossover_rate: 0.0` 与原始论文对齐 |
| **EoH** (Liu 等, 2024) | `dyca` | `init` + `e1` / `e2` / `m1` / `m2` | 任意 | DyCA 的算子命名继承自 EoH |
| **Multimodal EoH** | `dyca` | 在上述基础上扩展 `multimodal_*` 变种 | 返回 `BehaviorData` 的 evaluator | 设 `multimodal.enabled: true` 与 `behavior_storage: "rendered"` |
| **MEoH**（多目标 EoH） | `meoh` | `meoh_init` + `meoh_e1` / `meoh_e2` / `meoh_m1` / `meoh_m2` | 任意返回多指标的 evaluator | 设 `objective_metrics: [...]` |
| **ReEvo / 自我反思** | 任意 | 注入 `error_reflection` card 的自定义 mutation sampler | 任意 | 启用 `memory.auto_extraction.extract_bad: true` |
| **LLM-as-judge 基准** | 任意 | 默认 | `LLMJudgeEvaluator` | 可与 `mock` provider 配合用于低成本 dry run |
| **记忆增强进化** | 任意 | 默认 | 任意 | 启用 `memory.auto_extraction.enabled: true` 与 `extract_good` / `extract_bad` |

实现一种方法是修改一份配置文件，而非 fork 代码库。各编排器各自的字段表见[配置 § Evolution](configuration.md)。

## 配置示意

选择编排器仅需一个字段——`evolution.type`：

```yaml
evolution:
  type: "island_ga"   # 或 "dyca" 或 "meoh"
  max_generations: 30
  # ... 其余字段由匹配的 Pydantic schema 校验
```

`AppConfig` 使用 Pydantic 的 discriminated union，因此仅当前编排器允许的字段会被接受。配置错误的字段在启动时即被拒绝，而非被静默忽略。

## 同一任务三套配置：TSP

[TSP 示例](../examples/tsp.md)在同一任务上**同时附带**三套配置：

```
examples/applications/tsp_benchmark_python/
├── config.yaml                          # Island GA
├── tsp_dyca_config.yaml                 # DyCA
└── tsp_benchmark_meoh_config.yaml       # MEoH
```

依次运行三套配置，是建立"哪个编排器适用于具体问题"直觉的最直接路径。

## 新增编排器

编排器是一个仅承担两项职责的类——dispatch 与 survival：

```python
from llm4ad.orchestrator.base import BaseOrchestrator
from llm4ad.utils.registry import register_orchestrator

@register_orchestrator("my_method")
class MyOrchestrator(BaseOrchestrator):
    async def run(self) -> EvolutionResult:
        ...   # 循环：选 sampler、调 planner、接受或拒绝子代
```

若新方法还需要新的 prompt 模板，那属于 Sampler 类（`BasePlanner.register_sampler`），不需要变更编排器。新增 evaluator 同理：继承 `BaseEvaluator` 并应用 `@register_evaluator`。这些扩展均不要求修改不相关的代码——这正是[原子性带来的工程后果](../architecture/overview.md#原子性的意义)。

## 另见

- [架构概览](../architecture/overview.md) —— 五个组件，以及编排器在其中的位置。
- [架构数据流](../architecture/data-flow.md) —— 编排器在循环中所分发的对象。
- [Island GA](island-ga.md) · [DyCA](dyca.md) · [MEoH](meoh.md) —— 各编排器各自的配置字段。
- [配置指南](configuration.md) —— YAML schema。
