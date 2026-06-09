# LunarLander (Reinforcement Learning Policy)

End-to-end walkthrough of [`examples/applications/lunarlander_python/`](https://github.com/Optima-CityU/LLM4AD_Next/tree/main/examples/applications/lunarlander_python). The task is to evolve a control policy for the OpenAI Gym LunarLander environment that safely lands at `(0, 0)` across diverse initial conditions.

This example is the showcase for **RL policy search via LLM4AD**: the LLM proposes a policy (a `choose_action(observation)` function), the evaluator runs episodes in the gym environment, and the orchestrator selects the best generalizing policy.

## What evolves

The EVOLVE block lives in `lunarlander_policy/`:

```python
# EVOLVE_START
def choose_action(observation):
    """Return one of {0, 1, 2, 3} for nothing / left / main / right thrust.

    observation = (x, y, vx, vy, angle, ang_vel, leg1_contact, leg2_contact)
    """
    pass
# EVOLVE_END
```

The evaluator runs the policy across 35 dataset instances (`data/train/`), each with a different random seed producing different initial position, velocity, and angle.

## Two configs

```text
examples/applications/lunarlander_python/
├── lunarlander_benchmark_config.yaml   # Island GA, fastest path
└── lunarlander_dyca_config.yaml        # DyCA: cluster-aware specialists
```

DyCA shines here because the 35 seeds naturally fall into difficulty clusters (easy near-pad starts, harder long-range/high-rotation starts) and a specialist policy per cluster usually beats a single generalist.

## How to run

```bash
cd LLM4AD
uv sync --extra lunarlander          # installs gymnasium[box2d], matplotlib
uv sync --extra lunarlander --extra dyca   # for the DyCA variant

export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

# Island GA
llm4ad run examples/applications/lunarlander_python/lunarlander_benchmark_config.yaml

# DyCA — cluster-aware
llm4ad run examples/applications/lunarlander_python/lunarlander_dyca_config.yaml
```

The score is `episode_reward` (higher is better; ≥ 200 in OpenAI Gym is "solved"). The CLI prints the best score and the path to `best/` at end of run.

## Evaluator walkthrough

`lunarlander_evaluator.py:LunarLanderPolicyEvaluator` extends `BenchmarkEvaluator`. For each dataset file:

1. Loads the random seed.
2. Spawns a fresh `gymnasium.make("LunarLander-v2")` environment with that seed.
3. Runs an episode with the candidate `choose_action`, capping at the env's step limit.
4. Records metrics:
   - `episode_reward` — primary score (the CLI uses this since PR #96)
   - `fuel_consumed` — used main thruster ticks
   - `success` — landed safely flag
   - `execution_time_ms`
5. Returns `EvaluationResult(score=episode_reward, metrics={...})`.

Aggregation across 35 instances is mean reward — that's what the orchestrator selects on.

## Multimodal variant

[`lunarlander_python_multimodal/`](https://github.com/Optima-CityU/LLM4AD_Next/tree/main/examples/applications/lunarlander_python_multimodal) renders the trajectory as an image and feeds it into mutation prompts via the multimodal samplers. Useful when the LLM benefits from "seeing" why a policy crashes (e.g. drifting too far before braking).

```bash
llm4ad run examples/applications/lunarlander_python_multimodal/config.yaml
```

The evaluator emits a `BehaviorData(behavior_storage="rendered")` payload; `multimodal_mutation_sampler` and `multimodal_crossover_sampler` ingest those frames. See [Multimodal](../guides/multimodal.md) for the full mechanism.

## Reading the results

```bash
# Best policy worktree:
ls runs/lunarlander/<run_id>/best/code/
python runs/.../best/code/run_inference.py --seed 42  # try the policy

# DyCA only — per-cluster specialist worktrees:
ls runs/lunarlander_dyca/<run_id>/specialists/
```

The `state/evolution_state.json` exported per generation can be loaded into the Web UI's "rapid analysis" view to see how reward improved across generations and which clusters benefited from which operators.

## Variations to try

- **Different env**: swap `LunarLander-v2` to `BipedalWalker-v3` (also under `gymnasium[box2d]`); rewrite the `choose_action` signature accordingly.
- **MEoH multi-objective**: list `objective_metrics: ["episode_reward", "fuel_consumed"]` to evolve a Pareto front of "fuel-efficient" vs "high-reward" policies.
- **Trajectory visualizer**: enable `multimodal.enabled: true` even on the non-multimodal config to get the trajectory-rendered HTML in `state/`.

## See also

- [DyCA](../guides/dyca.md) — why clustering helps here
- [Multimodal](../guides/multimodal.md) — how images flow into prompts
- [Evaluators Guide](../guides/evaluators.md) — `BenchmarkEvaluator` aggregation
