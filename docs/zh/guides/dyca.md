# DyCA 编排器

DyCA（Dynamic Clustering Adaptive）适合**数据集中不同部分需要不同算法**的场景。它不试图进化出一个"包打天下"的解，而是按行为聚类数据集，对每个聚类进化出专门的专家算法（外加一个通才算法兜底）。

## 何时选

- 数据集异质（小 TSP vs 大 TSP；简单 vs 困难 ML 基准）。
- 你愿意把额外算力花在聚类与多池上。
- 你想看到不同区段的专家算法，而不只是一个全局赢家。

如果数据集大致同质，[Island GA](island-ga.md) 更简单，效果不会更差。

## 配置

```yaml
evolution:
  type: "dyca"
  max_generations: 30
  population_size: 8

  # 聚类
  n_clusters: 3
  clustering_method: "kmeans"          # 或 "agglomerative"
  recluster_interval: 5                # 重聚类检查间隔（代）
  ari_threshold: 0.8                   # ARI 高于此值则跳过重聚类
  n_anchors: 5                         # 每聚类的锚点算法数

  # 池
  generalist_pool_size: 10
  specialist_pool_size: 10
  complementary_pool_size: 10
  elite_archive_size: 5
  base_complementary_ratio: 0.2

  # SOS（停滞信号）逃逸
  sos_stagnation_threshold: 3

  offspring_per_generation: 5
  using_mode: false                    # 一旦聚类稳定可冻结
```

所有字段都在 `DyCAConfig`（`src/llm4ad/config/evolution.py`）中定义和校验，默认值也写在 schema 里。

## 工作机制（简版）

1. **锚点评估** — 启动时跑 `n_anchors × n_clusters` 个算法，给每个实例算出一个特征向量。
2. **实例聚类** — 在向量上跑 k-means（或层次聚类），得到 `n_clusters` 个实例组。
3. **按聚类进化** — 维护三种池：
   - **专家池**：每个聚类内表现最好的算法。
   - **通才池**：跨聚类表现都好的算法。
   - **互补池**：与池中已有成员强项互补的算法。
4. **存活选择** — 每个聚类各自保留专家；通才池占总预算的一定比例（由 `base_complementary_ratio` 控制）。
5. **重聚类检查** — 每隔 `recluster_interval` 代重聚类，与旧划分计算 ARI；`ari ≥ ari_threshold` 视为稳定，跳过本次。
6. **SOS 逃逸** — 连续 `sos_stagnation_threshold` 代无改进时强制做一次互补推动，跳出局部最优。

编排器实现在 `src/llm4ad/orchestrator/dyca.py`；规划器端的聚类感知采样器（`e1_sampler`、`e2_sampler`、`m1_sampler`、`m2_sampler`、`summary_sampler`、`complementary_cross_sampler`）在 `src/llm4ad/planner/sampler/dyca_samplers.py`。

## 算子

| 算子 | 采样器 | 用途 |
|---|---|---|
| `e1` | `e1_sampler` | 聚类感知探索：用聚类上下文生成新算法 |
| `e2` | `e2_sampler` | 跨聚类探索：组合两个聚类的信号 |
| `m1` | `m1_sampler` | 单父代的聚类感知变异 |
| `m2` | `m2_sampler` | 跳出当前策略的强力变异 |
| `summary` | `summary_sampler` | 总结一个聚类的精英算法，可作为通才种子 |
| `complementary_cross` | `complementary_cross_sampler` | 把专家与互补池成员交叉 |

这些采样器都列在 YAML 的 `planner.samplers:` 下，去掉某条即可禁用对应算子。

## 实战

TSP 示例与 Island GA、MEoH 的配置并排提供：

```bash
llm4ad run examples/applications/tsp_benchmark_python/tsp_dyca_config.yaml
```

它会对多样化数据集（小 / 聚集 / 大）做聚类，并为每个聚类产出专家求解器 — 可在运行摘要和 `runs/.../best/` 中看到。详见 [TSP 走读](../examples/tsp.md#编排器对比)。

## 调参

常用旋钮：

- **`n_clusters`**：从数据中明显的"区段数"开始，2–4 比较典型。
- **`n_anchors`**：锚点越多，特征向量越准，但前期 LLM 调用更多。3–7 较合理。
- **`recluster_interval`**：种群快速变化时调小（3–5），稳定后可调大（10+）。
- **`base_complementary_ratio`**：0.1–0.3。越大，跨聚类探索预算越多。
- **`using_mode: true`**：一旦聚类稳定，冻结分组，把预算全部用于专家进化。

## 相关链接

- [编排方法概览](orchestration.md) — 何时选 DyCA
- [Planner API](../api/planner.md) — 采样器链参考
- [配置指南](configuration.md) — DyCA 字段全表
- 源码权威：`src/llm4ad/orchestrator/dyca.py`
