# 规划器 API

`llm4ad.planner` 负责提出下一个待进化的算法。规划器把 LLM provider、采样器链和当前进化状态组合起来，发射 `Algorithm` 候选。当前内置两个规划器，都对接 `llm4ad.orchestrator` 中注册的编排器。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `BasePlanner` | 抽象规划器；继承并调用 `register_planner("name")` 即可新增 | `src/llm4ad/planner/base.py` |
| `LLMEvolutionPlanner` | Island GA 与 DyCA 的默认规划器（init / mutation / crossover，含可选多模态变体） | `src/llm4ad/planner/llm_evolution.py` |
| `MEoHEvolutionPlanner` | MEoH 编排器使用的存活式规划器 | `src/llm4ad/planner/meoh_evolution.py` |
| `Algorithm`、`AlgorithmInsight`、`InsightType` | 传给 coder + evaluator 的提案信封 | `src/llm4ad/planner/base.py` |
| `CodeArtifact`、`GenerationMetadata` | `Algorithm` 的代码侧载荷（完整内容或 unified diff） | `src/llm4ad/planner/base.py` |

## 采样器链

每个规划器会运行一条采样器链，采样器注册在 `llm4ad.planner.sampler` 下。每一步实际选择哪个采样器，取决于编排器和规划器调用的算子。

| 采样器系列 | 使用方 | 用途 |
|---|---|---|
| `init_sampler` / `multimodal_init_sampler` | 全部 | 生成初始种群 |
| `mutation_sampler` / `multimodal_mutation_sampler` | Island GA、DyCA | 单父代局部扰动 |
| `crossover_sampler` / `multimodal_crossover_sampler` | Island GA、DyCA | 两父代重组 |
| `e1_sampler`、`e2_sampler`、`m1_sampler`、`m2_sampler`、`summary_sampler`、`complementary_cross_sampler` | DyCA | 聚类感知算子（详见 [DyCA](../guides/dyca.md)） |
| `meoh_init_sampler`、`meoh_e1_sampler`、`meoh_e2_sampler`、`meoh_m1_sampler`、`meoh_m2_sampler` | MEoH | 多目标算子（详见 [MEoH](../guides/meoh.md)） |

每次运行启用的采样器列在 YAML 的 `planner.samplers` 下。当 `multimodal.enabled` 为 `false` 时，校验会拒绝 `multimodal_*` 采样器。

## 生成一个提案

```python
from llm4ad.planner.base import BasePlanner

BasePlanner.discover("llm4ad.planner")
planner = BasePlanner.create("llm_evolution", config=app_config, provider=provider, ...)

algorithm = await planner.propose(
    operator="mutation",
    parents=[parent_individual],
    state_tracker=state_tracker,
)
```

返回的 `Algorithm` 是编排器交给[编码器](coder.md)再交给[评估器](evaluator.md)的最小单元。它的 `code_artifacts` 可能处于 `full` 或 `diff` 内容模式；diff 模式下，需要用 `apply_unified_diff`（详见[工具](utils.md)）重建源码。

## 洞察类型

`InsightType` 记录提案的产生原因 — `INITIAL`、`MUTATION`、`CROSSOVER`、`REFLECTION`。它会随算法一起走完评估、再进入状态跟踪器，使得日志和可视化都能把改进归因到产生它的算子。

## 相关链接

- [编排方法概览](../guides/orchestration.md)
- [多模态](../guides/multimodal.md) — 何时启用多模态采样器
- 源码权威：`src/llm4ad/planner/`
