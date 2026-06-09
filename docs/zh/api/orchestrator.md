# 编排器 API

`llm4ad.orchestrator` 把规划器、编码器和评估器组装成一条进化循环。当前内置三种编排器，对应不同的搜索策略。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `BaseOrchestrator` | 抽象编排器；继承并调用 `register_orchestrator("name")` | `src/llm4ad/orchestrator/base.py` |
| `IslandGAOrchestrator` | 经典岛屿遗传算法（独立子种群 + 周期性迁移） | `src/llm4ad/orchestrator/island_ga.py` |
| `DyCAOrchestrator` | 动态聚类自适应进化（按问题实例聚类、多池资源分配） | `src/llm4ad/orchestrator/dyca.py` |
| `MEoHOrchestrator` | 多目标启发式进化，存活式 generation | `src/llm4ad/orchestrator/meoh.py` |
| `MEoHPopulation` | MEoH 的多目标种群管理（非支配排序、拥挤度） | `src/llm4ad/orchestrator/meoh_population.py` |
| `EvolutionResult`、`EvolutionCheckpoint` | 运行末态与检查点结构 | `src/llm4ad/orchestrator/base.py` |
| `EvolutionState`、`StateTracker` | 累积的种群、最佳个体、历史记录、轨迹 | `src/llm4ad/infra/state.py` |
| `EmbeddingClient` | 编排器内嵌的嵌入封装，用于轨迹分析 | `src/llm4ad/orchestrator/embedding_client.py` |
| `format_duration_ms` | 把毫秒格式化成 `1h 2min 3s` | `src/llm4ad/orchestrator/base.py` |

## 运行一次进化

最简单的方式是顶层入口：

```python
from llm4ad import LLM4AD

llm4ad = LLM4AD("config.yaml")
result = await llm4ad.run()              # 在内部装配编排器
print(result.best_individual.score)
```

如果只想直接用编排器：

```python
from llm4ad.orchestrator.base import BaseOrchestrator

BaseOrchestrator.discover("llm4ad.orchestrator")
orch = BaseOrchestrator.create(
    "dyca",
    config=app_config,
    planner=planner,
    coder=coder,
    evaluator=evaluator,
)
result: EvolutionResult = await orch.run()
```

## EvolutionResult 字段

| 字段 | 含义 |
|---|---|
| `state` | `EvolutionState` 枚举（`completed`、`failed`、`stopped`、…） |
| `best_individual` | 单目标运行的最佳 `Algorithm` |
| `final_population` | 单目标的最终种群；多目标的精英存档 |
| `final_generation` | 上次推进的代数 |
| `total_evaluations` | 评估调用总数 |
| `metadata.objective_metrics` | 多目标运行中的目标列表 |
| `metadata.elitist_archive` | 多目标 Pareto 存档（仅 MEoH 设置） |
| `metadata.per_objective_best` | 多目标运行的每目标最优值 |
| `duration_seconds` | 总墙钟时间 |

## 检查点 + 重启

`evolution.checkpoint_interval` 控制每多少代写一次 `EvolutionCheckpoint`。要继续：

```bash
llm4ad run config.yaml -r ./runs/proj/run-2026-05-13/checkpoints/last.json
```

或在 Python 中：

```python
result = await llm4ad.run(resume_from_checkpoint="checkpoints/last.json")
```

## `best/` 导出

每次运行结束后，`LLM4AD.run()` 会把最佳个体（多目标时是精英存档）的稳定快照写到运行目录的 `best/` 子目录下。CLI 在结束时打印路径（参见 `cli.py:184`）。多目标运行还会按 archive 索引创建 `best/pareto/<idx>/` 子目录。

## 各编排器要点

| 编排器 | 父代选择 | 后代生成 | 使用场景 |
|---|---|---|---|
| `island_ga` | 每岛独立选择 | 单父代变异、双父代交叉 | 简单多模态搜索；并行可解释 |
| `dyca` | 按聚类选择 | E1/E2/M1/M2/summary/complementary 算子 | 异构实例分布；要求专家化 |
| `meoh` | 多目标父代选择 | meoh_e1/e2/m1/m2 | 真正的多目标问题，需要 Pareto 前沿 |

详见 [编排方法概览](../guides/orchestration.md)。

## 相关链接

- [编排方法概览](../guides/orchestration.md)
- [DyCA](../guides/dyca.md) · [MEoH](../guides/meoh.md) · [Island GA](../guides/island-ga.md)
- 源码权威：`src/llm4ad/orchestrator/`
