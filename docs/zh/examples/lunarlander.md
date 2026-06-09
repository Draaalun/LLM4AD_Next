# LunarLander（强化学习策略）

[`examples/applications/lunarlander_python/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/lunarlander_python) 的端到端走读。任务是为 OpenAI Gym 的 LunarLander 环境进化一个控制策略，让飞船在不同初始条件下都能安全降落到 `(0, 0)`。

这个示例是 **LLM4AD 用于 RL 策略搜索** 的范例：LLM 提出策略（一个 `choose_action(observation)` 函数），评估器在 gym 环境里跑回合，编排器选出泛化最好的策略。

## 进化对象

EVOLVE 块在 `lunarlander_policy/` 中：

```python
# EVOLVE_START
def choose_action(observation):
    """返回 {0, 1, 2, 3} 之一：什么都不做 / 向左推 / 主推 / 向右推。

    observation = (x, y, vx, vy, angle, ang_vel, leg1_contact, leg2_contact)
    """
    pass
# EVOLVE_END
```

评估器在 35 个数据集实例（`data/train/`）上跑这个策略，每个实例随机种子不同 — 初始位置、速度、角度都各异。

## 两套配置

```text
examples/applications/lunarlander_python/
├── lunarlander_benchmark_config.yaml   # Island GA，最快上手
└── lunarlander_dyca_config.yaml        # DyCA：按聚类专家化
```

DyCA 在这里很合适：35 个种子天然分成难度聚类（贴近着陆台、长距离、高转动等），按聚类的专家策略通常优于单一通才。

## 怎么运行

```bash
cd LLM4AD
uv sync --extra lunarlander          # 装 gymnasium[box2d], matplotlib
uv sync --extra lunarlander --extra dyca   # DyCA 变体加这个

export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

# Island GA
llm4ad run examples/applications/lunarlander_python/lunarlander_benchmark_config.yaml

# DyCA — 聚类感知
llm4ad run examples/applications/lunarlander_python/lunarlander_dyca_config.yaml
```

分数是 `episode_reward`（越高越好；OpenAI Gym 中 ≥ 200 即"通关"）。CLI 在结束时打印最佳分数与 `best/` 路径。

## 评估器走读

`lunarlander_evaluator.py:LunarLanderPolicyEvaluator` 继承自 `BenchmarkEvaluator`。每个数据集文件：

1. 加载随机种子。
2. 用该种子 `gymnasium.make("LunarLander-v2")` 启动一个环境。
3. 用候选 `choose_action` 跑一回合，到环境的步数上限为止。
4. 记录指标：
   - `episode_reward` — 主分数（PR #96 起 CLI 使用此项）
   - `fuel_consumed` — 主推力使用 tick 数
   - `success` — 是否安全着陆
   - `execution_time_ms`
5. 返回 `EvaluationResult(score=episode_reward, metrics={...})`。

35 实例聚合方式为均值奖励，编排器在这之上做选择。

## 多模态变体

[`lunarlander_python_multimodal/`](https://github.com/llm4ad/llm4ad/tree/main/examples/applications/lunarlander_python_multimodal) 把轨迹渲染成图像，通过多模态采样器送进变异提示词。LLM 能直接"看到"策略为什么坠毁（比如刹车前漂得太远）时收益最大。

```bash
llm4ad run examples/applications/lunarlander_python_multimodal/config.yaml
```

评估器返回 `BehaviorData(behavior_storage="rendered")` 载荷；`multimodal_mutation_sampler` 和 `multimodal_crossover_sampler` 消费这些帧。完整机制见[多模态](../guides/multimodal.md)。

## 看结果

```bash
# 最佳策略工作树：
ls runs/lunarlander/<run_id>/best/code/
python runs/.../best/code/run_inference.py --seed 42  # 试一下策略

# 仅 DyCA — 各聚类的专家工作树：
ls runs/lunarlander_dyca/<run_id>/specialists/
```

按代导出的 `state/evolution_state.json` 可以在 Web UI 的"快速分析"中加载，能看到奖励曲线随代数的提升，以及哪些聚类受益于哪种算子。

## 可以试的变体

- **换环境**：把 `LunarLander-v2` 换成 `BipedalWalker-v3`（同样在 `gymnasium[box2d]` 下）；按需改 `choose_action` 签名。
- **MEoH 多目标**：列 `objective_metrics: ["episode_reward", "fuel_consumed"]`，进化"省油"与"高分"两个维度的 Pareto 前沿。
- **轨迹可视化**：即使在非多模态配置下，也可设 `multimodal.enabled: true`，可在 `state/` 看到渲染的 HTML 轨迹。

## 相关链接

- [DyCA](../guides/dyca.md) — 为什么聚类在这里有用
- [多模态](../guides/multimodal.md) — 图像如何进入提示词
- [评估器指南](../guides/evaluators.md) — `BenchmarkEvaluator` 聚合
