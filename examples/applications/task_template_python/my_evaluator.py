"""Evaluator template for Python design tasks in LLM4AD.

HOW TO USE THIS TEMPLATE:
    1. Copy this file and rename (e.g. my_task_evaluator.py)
    2. Search for "TODO" — each marks a location you MUST customize
    3. Lines without TODO are reusable boilerplate (don't change)
    4. Reference in YAML config: module: "my_evaluator.py:MyEvaluator"

SUBPROCESS ISOLATION:
    All evaluations run in a subprocess for fault isolation. LLM-generated
    code may segfault, deadlock, call sys.exit(), or leak memory — none of
    these can crash the main orchestrator when running in a subprocess.

    Two subprocess variants:
    - Separate script: evaluator spawns `python my_function.py '<json>'`
      (like TSP, Sorting). Use when the algorithm file already has a main().
    - Self-spawning: evaluator spawns `python my_evaluator.py '<json>'`
      (like LunarLander). Use when the evaluator needs to load the algorithm
      module and run a simulation/loop before returning results.

    This template uses the self-spawning pattern — the evaluate() method
    spawns this file as a subprocess, and the __main__ block at the bottom
    acts as the subprocess entry point. Adapt as needed for your task.

COMMON DATA FORMAT:
    One JSON file per instance. Each evaluate() call receives one JSON file
    via cfg.data_path. The dispatcher discovers files and aggregates results.

WORKTREE COMPATIBILITY:
    In production, the algorithm file lives in a git worktree (flat layout):
    - Local:    project_root/my_algorithm/my_function.py
    - Worktree: project_root/my_function.py
    Always check both paths.
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


# TODO: Change register name to your evaluator name (must match YAML module field)
@BaseEvaluator.register("my_task_evaluator")
# TODO: Rename class
class MyTaskEvaluator(BaseEvaluator):
    """Evaluator template for a custom Python design task.

    Spawns each evaluation as an isolated subprocess by invoking this file's
    __main__ block. The subprocess loads input data, runs the algorithm, and
    prints a JSON result to stdout.

    Benefits:
    - Segfaults, sys.exit(), memory leaks in generated code cannot crash
      the main orchestrator process.
    - True multi-instance parallelism via async subprocess (no GIL).
    - Timeout protection via asyncio.wait_for + proc.kill().
    """

    def __init__(self):
        """Initialize evaluator with metric definitions."""
        # TODO: Define metrics for your task. Each Metric must match
        # the `metrics` list in your YAML config.
        # MetricType.MAXIMIZE = higher is better (reward, accuracy)
        # MetricType.MINIMIZE = lower is better (time, error, cost)
        self._metrics = [
            Metric(
                name="primary_score",
                type=MetricType.MAXIMIZE,
                weight=1.0,
                description="Primary evaluation metric",
            ),
            Metric(
                name="execution_time_ms",
                type=MetricType.MINIMIZE,
                weight=0.1,
                description="Execution time in milliseconds",
            ),
        ]

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        # TODO: Return your evaluator name (should match register name)
        return "my_task_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    # ====================================================================
    # Main process side: spawn subprocess, parse result
    # ====================================================================

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate an algorithm implementation via subprocess.

        Spawns this file as a subprocess with the algorithm directory, data
        file path, and any additional parameters as a JSON argument. The
        subprocess runs the algorithm and prints a JSON result to stdout.

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

            # --- Step 1: Validate data file (boilerplate) ---
            if not data_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={},
                    success=False,
                    error_message=f"Data file not found: {data_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # --- Step 2: Find algorithm directory (worktree-compatible) ---
            # TODO: Change "my_algorithm" to your algorithm directory (repo) name
            # TODO: Change "my_function.py" to targeted algorithm filename
            algo_dir = project_root / "my_algorithm"
            if not algo_dir.exists():
                if (project_root / "my_function.py").exists():
                    algo_dir = project_root
                else:
                    return EvaluationResult(
                        score=0.0,
                        metrics={},
                        success=False,
                        error_message=f"Algorithm not found in {project_root}",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

            # --- Step 3: Spawn subprocess (boilerplate) ---
            input_json = json.dumps({
                "algo_dir": str(algo_dir),
                "data_path": str(data_path),
                # TODO(optional): Add extra parameters the subprocess needs
                # e.g. "seed": seed, "max_steps": max_steps
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

            # --- Step 4: Parse subprocess output (boilerplate) ---
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
            # TODO: Extract values from result dict and compute your score.
            # The result dict is whatever _run_algorithm() returns (see below).
            #
            # Score convention (higher is always better for evolution):
            #   MINIMIZE tasks (tour length, time): score = -value
            #   MAXIMIZE tasks (reward, accuracy):  score = value
            #   Composite: score = w1*metric1 + w2*metric2 + ...
            primary = result.get("primary_score", 0.0)
            score = float(primary)

            # TODO: Build metrics dict matching your _metrics definitions
            metrics = {
                "primary_score": score,
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

    # ====================================================================
    # Subprocess side: load algorithm, run evaluation, return JSON
    # ====================================================================

    @staticmethod
    def _run_algorithm(algo_dir: Path, data_path: Path) -> dict:
        """Run the algorithm on a single data instance (subprocess side).

        This method runs inside the isolated subprocess. It loads the
        algorithm, executes it on the input data, and returns a result dict.

        Two common patterns:

        1. Single-call (TSP/Sorting):
           algo_result = algo_func(input_data)

        2. Simulation loop (LunarLander/RL):
           for step in range(max_steps):
               action = algo_func(state)
               state, reward = env.step(action)

        Args:
            algo_dir: Directory containing the algorithm code.
            data_path: Path to the JSON data file for this instance.

        Returns:
            Dict with result fields. Must NOT contain "error" key on success.
            On failure, return {"error": "description"}.
        """
        import importlib.util

        start_time = time.time()

        # --- Load data (boilerplate) ---
        with open(data_path, encoding="utf-8") as f:
            test_data = json.load(f)

        # TODO: Extract input fields from your JSON data format
        # Examples:
        #   input_data = test_data["nodes"]              # TSP
        #   seed = test_data["seed"]                     # LunarLander
        #   input_data = test_data["input"]              # Generic
        input_data = test_data.get("input", [])
        expected = test_data.get("expected_output", None)

        # --- Load algorithm module (boilerplate, only change filename) ---
        # TODO: Change "my_function.py" to your algorithm filename
        module_file = algo_dir / "my_function.py"
        if not module_file.exists():
            return {"error": f"my_function.py not found in {algo_dir}"}

        module_name = f"_algo_{hash(str(module_file))}"
        spec = importlib.util.spec_from_file_location(module_name, str(module_file))
        if spec is None or spec.loader is None:
            return {"error": f"Cannot load module from {module_file}"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # TODO: Change "my_algorithm" to your function name in the module
        algo_func = module.my_algorithm

        # TODO: Implement your evaluation logic. This is the core of your task.
        # Single-call example:
        #   algo_result = algo_func(input_data)
        # Simulation/RL example:
        #   env = gym.make("LunarLander-v3")
        #   obs, _ = env.reset(seed=seed)
        #   for step in range(max_steps):
        #       action = algo_func(obs.tolist(), last_action, prev_obs.tolist())
        #       obs, reward, done, _, _ = env.step(action)
        #       if done: break
        try:
            algo_result = algo_func(input_data)
        except Exception as e:
            return {"error": f"Algorithm execution failed: {e}"}

        execution_time_ms = (time.time() - start_time) * 1000

        # TODO: Compute result metrics from algorithm output.
        # The keys here must match what evaluate() reads in Step 5.
        is_correct = algo_result == expected if expected is not None else True
        primary_score = 1.0 if is_correct else 0.0

        return {
            "primary_score": primary_score,
            "execution_time_ms": execution_time_ms,
            # TODO(optional): Add additional result fields
            # e.g. "tour_length": length, "fuel_consumed": fuel
        }


# ---------------------------------------------------------------------------
# Subprocess entry point (boilerplate — no changes needed)
# ---------------------------------------------------------------------------
# When this file is executed directly (python my_evaluator.py '<json>'),
# it loads the algorithm, runs the evaluation, and prints JSON to stdout.
# The evaluate() method above spawns this subprocess for fault isolation.


def _subprocess_main() -> None:
    """Run a single evaluation in an isolated subprocess."""
    if len(sys.argv) < 2:
        print("Usage: python my_evaluator.py '<json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    algo_dir = Path(input_data["algo_dir"])
    data_path = Path(input_data["data_path"])

    try:
        result = MyTaskEvaluator._run_algorithm(algo_dir, data_path)
    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()
