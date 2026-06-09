"""Custom evaluator for LunarLander policy algorithms.

This evaluator handles execution and result parsing for LunarLander
control policy implementations. The goal is to evolve a policy
that safely lands the lander at the target location (0, 0).

Each evaluate() call runs ONE episode with ONE seed (from a single
JSON data file). The dispatcher handles aggregation across instances.

SUBPROCESS ISOLATION: Each episode runs in a separate subprocess
(python evaluator.py '<json>') so that segfaults, deadlocks, or
sys.exit() in LLM-generated policy code cannot crash the main process.
The if __name__ == "__main__" block at the bottom is the subprocess
entry point.
"""

import asyncio
import importlib.util
import json
import sys
import time
from pathlib import Path

import gymnasium as gym

from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvalContext,
    EvaluationResult,
    Metric,
    MetricType,
)


@BaseEvaluator.register("lunarlander_policy_evaluator")
class LunarLanderPolicyEvaluator(BaseEvaluator):
    """Evaluator for LunarLander control policies.

    Spawns each episode as an isolated subprocess (Pattern A) by invoking
    this file's __main__ block. The subprocess loads the policy module,
    runs the episode with gymnasium, and prints a JSON result to stdout.

    Benefits over in-process evaluation:
    - Segfaults, sys.exit(), or memory leaks in policy code cannot crash
      the main orchestrator process.
    - True multi-instance parallelism via async subprocess (no GIL).
    - Timeout protection via asyncio.wait_for + proc.kill().

    Each evaluate() call handles a single instance (one seed from one JSON
    data file). The dispatcher aggregates results across all instances.
    """

    def __init__(self):
        """Initialize the evaluator with metric definitions."""
        self._metrics = [
            Metric(
                name="episode_reward",
                type=MetricType.MAXIMIZE,
                weight=1.0,
                description="Total reward obtained during episode (higher is better, safe landing ~200)",
            ),
            Metric(
                name="execution_time_ms",
                type=MetricType.MINIMIZE,
                weight=0.1,
                description="Execution time in milliseconds",
            ),
            Metric(
                name="fuel_consumed",
                type=MetricType.MINIMIZE,
                weight=0.2,
                description="Number of actions that consumed fuel (actions 1, 2, 3)",
            ),
            Metric(
                name="success",
                type=MetricType.MAXIMIZE,
                weight=5.0,
                description="Whether the landing was successful (1.0) or not (0.0)",
            ),
        ]

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return "lunarlander_policy_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    def _load_policy_module(self, policy_dir: Path):
        """Load a policy module from a given directory by absolute file path.

        Uses importlib.util.spec_from_file_location() to load the module
        directly from its file path, bypassing sys.modules. This avoids
        the bug where importlib.import_module("choose_action") returns a
        cached module from a different algorithm's worktree.

        Args:
            policy_dir: Path to the directory containing choose_action.py.

        Returns:
            The loaded policy module.
        """
        file_path = policy_dir / "choose_action.py"
        if not file_path.exists():
            raise FileNotFoundError(f"choose_action.py not found in {policy_dir}")

        # Use the absolute path as a unique module name to avoid collisions
        module_name = f"_policy_{id(self)}_{hash(str(file_path))}"

        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module spec from {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run_episode(
        self,
        policy_func,
        seed: int,
        max_steps: int = 200,
    ) -> dict:
        """Run a single LunarLander episode with the given policy.

        Args:
            policy_func: The choose_action(s, last_action, s_pre) function.
            seed: Random seed for the environment.
            max_steps: Maximum steps per episode.

        Returns:
            Dict with episode results.
        """
        env = gym.make(
            "LunarLander-v3",
            gravity=-10.0,
            enable_wind=False,
            wind_power=15.0,
            turbulence_power=1.5,
            render_mode=None,
        )

        observation, _ = env.reset(seed=seed)
        action = 0
        episode_reward = 0.0
        fuel_consumed = 0
        pre_observation = observation.copy()

        start_time = time.time()
        for step in range(max_steps + 1):
            try:
                action = policy_func(
                    observation.tolist(), action, pre_observation.tolist()
                )
            except Exception as e:
                env.close()
                return {
                    "error": f"Policy function failed at step {step}: {e}",
                    "episode_reward": -1000,
                    "fuel_consumed": max_steps,
                    "success": 0.0,
                    "steps": step,
                }

            if action not in [0, 1, 2, 3]:
                action = 0

            pre_observation = observation.copy()
            observation, reward, done, truncated, _info = env.step(action)
            episode_reward += reward

            if action in [1, 2, 3]:
                fuel_consumed += 1

            if done or truncated:
                break

        env.close()
        execution_time_ms = (time.time() - start_time) * 1000.0
        success = 1.0 if episode_reward >= 200.0 else 0.0

        return {
            "episode_reward": episode_reward,
            "fuel_consumed": fuel_consumed,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "steps": step,
        }

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate a LunarLander policy on a single instance via subprocess.

        Spawns this file as a subprocess with the policy directory, seed, and
        max_steps as a JSON argument. The subprocess loads the policy, runs
        the episode, and prints a JSON result to stdout.

        Args:
            cfg: EvalContext with project_root, data_path, timeout.

        Returns:
            EvaluationResult for this single instance.
        """
        start_time = time.time()

        try:
            project_root = Path(cfg.project_root)
            data_path = Path(cfg.data_path)

            # --- Load instance config from JSON ---
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000.0,
                )

            with open(data_path, encoding="utf-8") as f:
                instance = json.load(f)

            seed = instance.get("seed", 42)
            max_steps = instance.get("max_steps", 200)

            # --- Find policy directory (worktree-compatible) ---
            policy_dir = project_root / "policy"
            if not policy_dir.exists():
                if (project_root / "choose_action.py").exists():
                    policy_dir = project_root
                else:
                    return EvaluationResult(
                        score=0.0,
                        metrics={},
                        success=False,
                        error_message=f"Policy directory not found in {project_root}",
                        duration_ms=(time.time() - start_time) * 1000.0,
                    )

            # --- Spawn subprocess for isolated episode evaluation ---
            input_json = json.dumps({
                "policy_dir": str(policy_dir),
                "seed": seed,
                "max_steps": max_steps,
            })

            evaluator_script = str(Path(__file__).resolve())

            proc = await asyncio.create_subprocess_exec(
                sys.executable, evaluator_script, input_json,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=cfg.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Evaluation timed out after {cfg.timeout}s",
                    duration_ms=cfg.timeout * 1000,
                )

            duration_ms = (time.time() - start_time) * 1000.0
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Subprocess failed (rc={proc.returncode}): {stderr_text[:500]}",
                    duration_ms=duration_ms,
                )

            # --- Parse subprocess output ---
            try:
                result = json.loads(stdout_text.strip())
            except json.JSONDecodeError:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Invalid JSON output: {stdout_text[:200]}",
                    duration_ms=duration_ms,
                )

            if "error" in result:
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=result["error"],
                    duration_ms=duration_ms,
                )

            # --- Compute score and metrics ---
            episode_reward = result["episode_reward"]
            fuel = result["fuel_consumed"]
            success_val = result["success"]
            exec_time_ms = result["execution_time_ms"]

            # Weighted composite score
            score = (
                (episode_reward / 200.0) * 0.6
                + success_val * 0.2
                + (1.0 - min(fuel / 100.0, 1.0)) * 0.2
            )

            metrics = {
                "score": float(score),
                "episode_reward": float(episode_reward),
                "fuel_consumed": float(fuel),
                "success": float(success_val),
                "execution_time_ms": exec_time_ms,
            }

            return EvaluationResult(
                score=episode_reward,
                metrics=metrics,
                success=True,
                duration_ms=duration_ms,
                metadata={
                    "seed": seed,
                    "max_steps": max_steps,
                    "steps_taken": result.get("steps", 0),
                    "dataset": str(data_path),
                },
            )

        except Exception as e:
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=f"Evaluation error: {e}",
                duration_ms=(time.time() - start_time) * 1000.0,
            )


# ---------------------------------------------------------------------------
# Subprocess entry point
# ---------------------------------------------------------------------------
# When this file is executed directly (python lunarlander_evaluator.py '<json>'),
# it loads the policy, runs one episode, and prints JSON to stdout.
# The evaluate() method above spawns this subprocess for fault isolation.


def _subprocess_main() -> None:
    """Run a single episode in an isolated subprocess."""
    if len(sys.argv) < 2:
        print("Usage: python lunarlander_evaluator.py '<json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    policy_dir = Path(input_data["policy_dir"])
    seed = input_data.get("seed", 42)
    max_steps = input_data.get("max_steps", 200)

    evaluator = LunarLanderPolicyEvaluator()

    try:
        module = evaluator._load_policy_module(policy_dir)
        if not hasattr(module, "choose_action"):
            result = {"error": "choose_action function not found in policy module"}
        else:
            result = evaluator._run_episode(module.choose_action, seed, max_steps)
    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()
