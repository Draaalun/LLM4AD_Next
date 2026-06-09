"""Evaluator template for bipedal_walker task in LLM4AD.

HOW TO USE THIS TEMPLATE:
    1. Copy this file and rename (e.g. bipedal_walker_evaluator.py)
    2. Search for "TODO" — each marks a location you MUST customize
    3. Lines without TODO are reusable boilerplate (don't change)
    4. Reference in YAML config: module: "bipedal_walker_evaluator.py:BipedalWalkerEvaluator"

SUBPROCESS ISOLATION:
    All evaluations run in a subprocess for fault isolation. LLM-generated
    code may segfault, deadlock, call sys.exit(), or leak memory — none of
    these can crash the main orchestrator when running in a subprocess.

    This template uses the self-spawning pattern — the evaluate() method
    spawns this file as a subprocess, and the __main__ block at the bottom
    acts as the subprocess entry point.

COMMON DATA FORMAT:
    One JSON file per instance. Each evaluate() call receives one JSON file
    via cfg.data_path. The dispatcher discovers files and aggregates results.

    For bipedal_walker, the data file contains a JSON object with a "seeds"
    list (list of integers) that are used as environment seeds for each
    evaluation episode. Mean score is averaged over episodes.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvalContext,
    EvaluationResult,
    Metric,
    MetricType,
)


@BaseEvaluator.register("bipedal_walker_evaluator")
class BipedalWalkerEvaluator(BaseEvaluator):
    """Evaluator for bipedal_walker controller task.

    Spawns each evaluation as an isolated subprocess by invoking this file's
    __main__ block. The subprocess loads controller, runs multiple episodes
    of BipedalWalker-v3, and prints a JSON result to stdout.
    """

    def __init__(self):
        """Initialize evaluator with metric definitions."""
        self._metrics = [
            Metric(
                name="mean_score",
                type=MetricType.MAXIMIZE,
                weight=1.0,
                description="Average total reward over evaluation episodes (truncated at 1600 steps).",
            ),
        ]

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return "bipedal_walker_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate an algorithm implementation via subprocess.

        Spawns this file as a subprocess with the algorithm directory, data
        file path, and any additional parameters as a JSON argument. The
        subprocess runs the controller and prints a JSON result to stdout.

        Args:
            cfg: EvalContext with:
                - cfg.project_root: path to algorithm directory (worktree or local)
                - cfg.data_path: path to the data file for this evaluation
                - cfg.timeout: max execution time in seconds

        Returns:
            EvaluationResult with score, metrics, and metadata.
        """
        start_time = time.time()

        try:
            project_root = Path(cfg.project_root)
            data_path = Path(cfg.data_path)

            # --- Step 1: Validate data file ---
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # --- Step 2: Find algorithm directory (worktree-compatible) ---
            # Algorithm dir is "bipedal_walker_algorithm", file is "controller.py"
            algo_dir = project_root / "bipedal_walker_algorithm"
            if not algo_dir.exists():
                # Check flat worktree layout
                if (project_root / "controller.py").exists():
                    algo_dir = project_root
                else:
                    return EvaluationResult(
                        score=0.0,
                        metrics={},
                        success=False,
                        error_message=f"Algorithm not found in {project_root}",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

            # --- Step 3: Spawn subprocess ---
            input_json = json.dumps({
                "algo_dir": str(algo_dir),
                "data_path": str(data_path),
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

            duration_ms = (time.time() - start_time) * 1000
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

            # --- Step 4: Parse subprocess output ---
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

            # --- Step 5: Compute score from subprocess result ---
            mean_score = result.get("mean_score", 0.0)
            score = float(mean_score)  # maximize, so score = mean_score

            metrics = {
                "mean_score": score,
                "execution_time_ms": result.get("execution_time_ms", duration_ms),
            }

            return EvaluationResult(
                score=score,
                metrics=metrics,
                success=True,
                duration_ms=duration_ms,
                metadata={
                    "dataset": str(data_path),
                },
            )

        except Exception as e:
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=f"Evaluation error: {e}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    @staticmethod
    def _run_algorithm(algo_dir: Path, data_path: Path) -> dict:
        """Run the controller on BipedalWalker-v3 (subprocess side).

        This method runs inside the isolated subprocess. It loads the
        controller, runs multiple episodes, and returns a result dict.

        Args:
            algo_dir: Directory containing the algorithm code.
            data_path: Path to the JSON data file for this instance.

        Returns:
            Dict with result fields. Must NOT contain "error" key on success.
            On failure, return {"error": "description"}.
        """
        import importlib.util

        start_time = time.time()

        # --- Load data ---
        with open(data_path, encoding="utf-8") as f:
            test_data = json.load(f)

        seeds = test_data.get("seeds", [42])  # default one episode if missing
        num_episodes = len(seeds)
        max_steps = 1600

        # --- Load controller module ---
        module_file = algo_dir / "controller.py"
        if not module_file.exists():
            return {"error": f"controller.py not found in {algo_dir}"}

        module_name = f"_algo_{hash(str(module_file))}"
        spec = importlib.util.spec_from_file_location(module_name, str(module_file))
        if spec is None or spec.loader is None:
            return {"error": f"Cannot load module from {module_file}"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # The evolvable function must be named "walker_controller"
        if not hasattr(module, "walker_controller"):
            return {"error": "Module does not contain 'walker_controller' function."}

        controller_fn = module.walker_controller

        # --- Run evaluation episodes ---
        try:
            import gymnasium as gym
        except ImportError:
            return {"error": "gymnasium is required for evaluation but not installed."}

        total_reward = 0.0
        for episode_idx, seed in enumerate(seeds):
            env = gym.make("BipedalWalker-v3", render_mode=None)
            obs, _ = env.reset(seed=seed)
            episode_reward = 0.0
            for step in range(max_steps):
                # Ensure observation is a list of floats
                if not isinstance(obs, (list, tuple)):
                    obs_list = obs.tolist()
                else:
                    obs_list = list(obs)
                action = controller_fn(obs_list)
                # Clip action to [-1, 1] (controller may not clip)
                action_clipped = [max(-1.0, min(1.0, a)) for a in action]
                obs, reward, terminated, truncated, _ = env.step(action_clipped)
                episode_reward += reward
                if terminated or truncated:
                    break
            total_reward += episode_reward
            env.close()

        mean_score = total_reward / num_episodes
        execution_time_ms = (time.time() - start_time) * 1000

        return {
            "mean_score": mean_score,
            "execution_time_ms": execution_time_ms,
        }


def _subprocess_main() -> None:
    """Run a single evaluation in an isolated subprocess."""
    if len(sys.argv) < 2:
        print("Usage: python bipedal_walker_evaluator.py '<json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    algo_dir = Path(input_data["algo_dir"])
    data_path = Path(input_data["data_path"])

    try:
        result = BipedalWalkerEvaluator._run_algorithm(algo_dir, data_path)
    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()