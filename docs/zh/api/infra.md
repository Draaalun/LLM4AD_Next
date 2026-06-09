# 基础设施 API

`llm4ad.infra` 是各模块共享的低层基础设施。多数用户不会直接 import 这里的内容，但当编排器、评估器或自定义集成需要状态、计时、版本控制或仓库分析时，这些就是出入口。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `StateTracker`、`EvolutionState` | 跨代累积种群、最佳个体、历史轨迹 | `src/llm4ad/infra/state.py` |
| `BestExporter` | `best/` 导出器 — 将最终最优快照写到稳定路径 | `src/llm4ad/infra/best_exporter.py` |
| `ExecutionTiming`、`TimingPhase` | provider/coder/evaluator 调用的细粒度耗时 | `src/llm4ad/infra/timing.py` |
| `BaseVersionControl`、`WorktreeInfo`、`VersionControlConfig` | git 工作树管理（多个并发个体的隔离） | `src/llm4ad/infra/version_control/` |
| `inspect_path`、`clean_path`、`AnalyzedRepository` | EVOLVE 标记检测 + 移除（`llm4ad evolve check/clean` 后端） | `src/llm4ad/infra/repo_analyzer/` |
| `EvolveDetector` | EVOLVE 标记的扫描器/解析器（识别 nested、unbalanced 标记） | `src/llm4ad/infra/repo_analyzer/detector.py` |
| `BaseProvider`、`OpenAICompatibleProvider`、… | LLM provider — 详见独立的 [Provider API](provider.md) | `src/llm4ad/infra/provider/` |
| `BaseRunMonitor` | 运行进度监控器钩子（CLI 进度条、Web UI 推送） | `src/llm4ad/infra/monitor/` |

## 状态跟踪

```python
from llm4ad.infra.state import StateTracker

tracker = StateTracker()
tracker.record_individual(algorithm, evaluation_result)
tracker.record_generation(gen_index, best_so_far)
tracker.save_checkpoint(path="checkpoints/gen10.json")
```

`StateTracker` 把 trajectory 以 JSON 持久化到运行目录的 `state/evolution_state.json`，前端 Web UI 的"快速进化分析"读它来渲染轨迹图。

## 计时

`ExecutionTiming` 是一个轻量结构，附在每次 LLM 调用、coder 调用和 evaluator 结果上。它把端到端耗时拆成阶段（请求构造、网络等待、流式解析、后处理）。

```python
from llm4ad.infra.timing import ExecutionTiming

timing = ExecutionTiming()
with timing.phase("network"):
    response = await provider.chat(messages)
print(timing.total_ms, timing.phases)
```

详见[计时与指标](../guides/timing-metrics.md)。

## 仓库分析（EVOLVE 标记）

```python
from llm4ad.infra.repo_analyzer import inspect_path, clean_path

result = inspect_path("examples/applications/sorting_benchmark_python")
print(result.summary["blocks"], result.active_block_id)

# 干跑：报告会被移除哪些行，但不写盘
clean = clean_path("examples/applications/sorting_benchmark_python")
# 真正改写：
clean = clean_path("examples/applications/sorting_benchmark_python", apply=True)
```

CLI 中：`llm4ad evolve check` 和 `llm4ad evolve clean`（详见 [CLI 参考](../guides/cli.md#evolve)）。

## 版本控制 / 工作树

`BaseVersionControl` 为每个候选算法创建一个 git 工作树，用完即弃，避免污染主分支。`VersionControlConfig` 在 YAML 的 `version_control:` 下配置（默认值通常无需调整）。

## 嵌入

虽然嵌入支持在 `llm4ad.orchestrator` 下（`EmbeddingClient`、`embedding_utils.py`），其后端 provider 仍然在 `llm4ad.infra.provider` 中注册。批量嵌入和 `local` 双端点模式见 [Embeddings 与轨迹](../guides/embeddings.md)。

## 相关链接

- [配置指南](../guides/configuration.md) — `version_control:`、`logging:`、`workspace:`
- [计时与指标](../guides/timing-metrics.md) — 详细计时
- 源码权威：`src/llm4ad/infra/`
