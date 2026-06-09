"""Custom evaluator for LunarLander policy algorithms (multimodal version).

This evaluator extends the text-only version by generating trajectory
visualizations as behavior data. These images are returned as
BehaviorData so that the multimodal evolution loop can include them
in LLM prompts, allowing the LLM to visually diagnose landing behavior.

Architecture (clean separation of concerns):
- ``_run_episode``: runs the gym episode, captures frames, composites
  a trajectory canvas. Returns metrics + raw behavior data (canvas).
  No rendering, no observation text — those are separate concerns.
- ``_render_trajectory_image``: converts a raw canvas to an annotated
  base64 PNG. Called by the deferred renderer or the subprocess.
- ``_build_observation_text``: builds LLM-readable text from metrics.
  Called in the main process after the subprocess returns.
- ``evaluate()``: orchestrates subprocess, computes score, builds
  BehaviorData using the standard multimodal pattern.

SUBPROCESS ISOLATION: Each episode runs in a separate subprocess.
The subprocess returns metrics + raw_behavior (or pre-rendered PNG,
depending on behavior_storage mode) via JSON stdout.
"""

import asyncio
import base64
import copy
import importlib.util
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np

from llm4ad.config.schema import EvalContext
from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvaluationResult,
    Metric,
    MetricType,
)
from llm4ad.evaluator.behavior import BehaviorData, BehaviorVisualization
from llm4ad.evaluator.renderer import BaseRenderer

# ===========================================================================
# Visualization helpers (task-specific — customize for your domain)
# ===========================================================================
# These functions handle rendering and observation text generation.
# They are separate from the episode runner so that each concern
# (execution, rendering, observation) is independently replaceable.


def _composite_trajectory(
    frames: list[tuple[int, np.ndarray]],
    max_steps: int,
    canvas_shape: tuple[int, int, int] = (400, 600, 3),
) -> np.ndarray:
    """Composite rendered frames into a trajectory overlay canvas.

    Each frame is blended onto the canvas with increasing alpha,
    creating a fading-trail effect that shows the lander's full path
    (adapted from MLES v1 reference implementation).

    Args:
        frames: List of (step_number, rgb_array) tuples captured
            during episode execution.
        max_steps: Maximum episode steps (used for alpha normalization).
        canvas_shape: Shape of the output canvas (H, W, C).

    Returns:
        Numpy array (H, W, 3) with the composited trajectory.
    """
    canvas = np.zeros(canvas_shape, dtype=np.float32)
    for step, img in frames:
        if img is None:
            continue
        mask = np.any(img != [0, 0, 0], axis=-1)
        alpha = min(step / max_steps, 1.0)
        canvas[mask] = canvas[mask] * (1 - alpha) + img[mask] * alpha
    return canvas


def _render_trajectory_image(
    canvas: np.ndarray,
    reward: float,
    final_state: str,
    seed: int,
) -> str:
    """Render the trajectory canvas to an annotated base64 PNG image.

    Uses matplotlib (Agg backend) to add title with reward, seed,
    and landing outcome, then encodes to base64.

    Args:
        canvas: Numpy array (H, W, 3) from ``_composite_trajectory()``.
        reward: Episode reward for title annotation.
        final_state: Landing outcome string (e.g., "Landed safely").
        seed: Random seed used for the episode.

    Returns:
        Base64-encoded PNG string.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.imshow(canvas.astype(np.uint8))
    ax.set_title(
        f"Lander Trajectory (seed={seed})\n"
        f"Reward: {reward:.1f} | {final_state}",
        fontsize=12,
    )
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _build_observation_text(
    final_obs: list[float] | np.ndarray,
    reward: float,
    fuel: int,
    final_state: str,
    seed: int,
    steps: int,
) -> str:
    """Build a human/LLM-readable observation text from episode results.

    Called in the main process after the subprocess returns metrics.

    Args:
        final_obs: Final 8-element observation vector.
        reward: Total episode reward.
        fuel: Number of fuel-consuming actions.
        final_state: Landing outcome string.
        seed: Random seed used.
        steps: Total steps taken.

    Returns:
        Formatted observation string.
    """
    return (
        f"Seed={seed} | Reward={reward:.1f} | "
        f"Fuel={fuel} | State={final_state} | "
        f"Steps={steps}\n"
        f"Final state: x={final_obs[0]:.3f}, y={final_obs[1]:.3f}, "
        f"vx={final_obs[2]:.3f}, vy={final_obs[3]:.3f}, "
        f"angle={final_obs[4]:.3f}, angular_vel={final_obs[5]:.3f}, "
        f"left_leg={final_obs[6]:.0f}, right_leg={final_obs[7]:.0f}"
    )


# ===========================================================================
# Deferred renderer (for raw mode — registered in BaseRenderer registry)
# ===========================================================================
# When behavior_storage is "raw", the evaluator stores compact canvas data
# instead of pre-rendered PNGs. This renderer reconstructs the image on
# demand (e.g., when a sampler needs to embed it in an LLM prompt).
#
# raw_data schema:
#   {
#       "canvas": list[list[list[int]]],  # (H, W, 3) pixel values 0-255
#       "reward": float,
#       "final_state": str,               # "Landed safely" / "Crashed" / "Timed out"
#       "seed": int
#   }


@BaseRenderer.register("lunarlander_trajectory")
class LunarLanderTrajectoryRenderer(BaseRenderer):
    """Render a LunarLander trajectory image from stored canvas data.

    Converts the raw canvas (nested Python lists) back to a numpy array
    and produces an annotated matplotlib figure identical to the one the
    evaluator generates at evaluation time.
    """

    def render(self, raw_data: dict[str, Any], **kwargs: Any) -> str:
        """Render raw canvas data to an annotated base64 PNG.

        Args:
            raw_data: Dict with ``canvas``, ``reward``, ``final_state``,
                ``seed`` keys.
            **kwargs: Unused.

        Returns:
            Base64-encoded PNG string.
        """
        canvas = np.array(raw_data["canvas"], dtype=np.uint8)
        reward = raw_data.get("reward", 0.0)
        final_state = raw_data.get("final_state", "Unknown")
        seed = raw_data.get("seed", 0)

        return _render_trajectory_image(canvas, reward, final_state, seed)


# ===========================================================================
# Evaluator class
# ===========================================================================


@BaseEvaluator.register("lunarlander_policy_evaluator_multimodal")
class LunarLanderPolicyEvaluatorMultimodal(BaseEvaluator):
    """Evaluator for LunarLander control policies with trajectory visualization.

    Extends the base evaluator to generate trajectory overlay images.
    The subprocess captures frames at regular intervals and composites
    them onto a canvas with alpha blending, producing raw behavior data
    that the renderer converts to annotated PNG images.
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
        return "lunarlander_policy_evaluator_multimodal"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    def _load_policy_module(self, policy_dir: Path):
        """Load a policy module from a given directory by absolute file path.

        Args:
            policy_dir: Path to the directory containing choose_action.py.

        Returns:
            The loaded policy module.
        """
        file_path = policy_dir / "choose_action.py"
        if not file_path.exists():
            raise FileNotFoundError(f"choose_action.py not found in {policy_dir}")

        module_name = f"_policy_{id(self)}_{hash(str(file_path))}"
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module spec from {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # ------------------------------------------------------------------
    # Subprocess side: episode execution + raw behavior capture
    # ------------------------------------------------------------------

    def _run_episode(
        self,
        policy_func,
        seed: int,
        max_steps: int = 200,
        capture_behavior: bool = True,
        render_interval: int = 10,
    ) -> dict:
        """Run a single LunarLander episode and optionally capture raw behavior.

        This method runs inside the subprocess. It ONLY handles episode
        execution and raw data capture — no image rendering, no
        observation text. Those are separate concerns handled downstream.

        Args:
            policy_func: The choose_action(s, last_action, s_pre) function.
            seed: Random seed for the environment.
            max_steps: Maximum steps per episode.
            capture_behavior: Whether to capture frames for visualization.
                Set to False when behavior_storage is "none" for speed.
            render_interval: Capture a frame every N steps.

        Returns:
            Dict with episode metrics and optionally raw_behavior data.
        """
        env = gym.make(
            "LunarLander-v3",
            gravity=-10.0,
            enable_wind=False,
            wind_power=15.0,
            turbulence_power=1.5,
            render_mode="rgb_array" if capture_behavior else None,
        )

        observation, _ = env.reset(seed=seed)
        action = 0
        episode_reward = 0.0
        fuel_consumed = 0
        pre_observation = copy.deepcopy(observation)

        frames: list[tuple[int, np.ndarray]] = []
        flash_counter = 0

        # Take initial step
        observation, reward, done, truncated, _info = env.step(action)

        start_time = time.time()
        final_step = 0
        for step in range(max_steps + 1):
            final_step = step
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

            pre_observation = copy.deepcopy(observation)
            observation, reward, done, truncated, _info = env.step(action)
            episode_reward += reward

            if action in [1, 2, 3]:
                fuel_consumed += 1

            # Capture frame at regular intervals for trajectory visualization
            if capture_behavior and flash_counter >= render_interval:
                img = env.render()
                if img is not None:
                    frames.append((step, img))
                flash_counter = 0

            flash_counter += 1

            if done or truncated:
                if capture_behavior:
                    img = env.render()
                    if img is not None:
                        frames.append((step, img))
                break

        env.close()
        execution_time_ms = (time.time() - start_time) * 1000.0
        success = 1.0 if episode_reward >= 200.0 else 0.0

        # Determine landing state
        if done and episode_reward >= 200:
            final_state = "Landed safely"
        elif done:
            final_state = "Crashed"
        else:
            final_state = "Timed out"

        # Build raw behavior data (canvas) if frames were captured
        raw_behavior = None
        if capture_behavior and frames:
            canvas = _composite_trajectory(frames, max_steps)
            raw_behavior = {
                "canvas": canvas.astype(np.uint8).tolist(),
                "reward": float(episode_reward),
                "final_state": final_state,
                "seed": seed,
            }

        return {
            "episode_reward": episode_reward,
            "fuel_consumed": fuel_consumed,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "steps": final_step,
            "final_observation": observation.tolist(),
            "final_state": final_state,
            "raw_behavior": raw_behavior,
        }

    # ------------------------------------------------------------------
    # Main process side: subprocess orchestration + BehaviorData
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        cfg: EvalContext,
    ) -> EvaluationResult:
        """Evaluate a LunarLander policy on a single instance via subprocess.

        Follows the standard multimodal evaluator pattern:
        - Steps 1-4: Subprocess management (boilerplate)
        - Step 5: Score + metrics computation
        - Step 6: Build BehaviorData from subprocess result

        Args:
            cfg: EvalContext with project_root, data_path, timeout,
                and behavior_storage mode.

        Returns:
            EvaluationResult with BehaviorData containing the trajectory image.
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
                    duration_ms=(time.time() - start_time) * 1000.0,
                )

            # --- Step 2: Load instance config ---
            with open(data_path, encoding="utf-8") as f:
                instance = json.load(f)

            seed = instance.get("seed", 42)
            max_steps = instance.get("max_steps", 200)

            # --- Step 3: Find policy directory (worktree-compatible) ---
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

            # --- Step 4: Spawn subprocess ---
            input_json = json.dumps({
                "policy_dir": str(policy_dir),
                "seed": seed,
                "max_steps": max_steps,
                "behavior_storage": cfg.behavior_storage,
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

            # --- Step 5: Compute score and metrics ---
            episode_reward = result["episode_reward"]
            fuel = result["fuel_consumed"]
            success_val = result["success"]
            exec_time_ms = result["execution_time_ms"]

            score = (
                (episode_reward / 200.0) * 0.5
                + success_val * 0.3
                + (1.0 - min(fuel / 100.0, 1.0)) * 0.1
                + (1.0 - min(exec_time_ms / 10000.0, 1.0)) * 0.1
            )

            metrics = {
                "score": float(score),
                "episode_reward": float(episode_reward),
                "fuel_consumed": float(fuel),
                "success": float(success_val),
                "execution_time_ms": exec_time_ms,
            }

            # --- Step 6: Build BehaviorData (multimodal addition) ---
            behavior = None
            behavior_storage = cfg.behavior_storage

            if behavior_storage != "none":
                # 6a. Build observation text from subprocess metrics
                final_obs = result.get("final_observation", [0.0] * 8)
                final_state = result.get("final_state", "Unknown")
                obs_text = _build_observation_text(
                    final_obs=final_obs,
                    reward=episode_reward,
                    fuel=fuel,
                    final_state=final_state,
                    seed=seed,
                    steps=result.get("steps", 0),
                )

                # 6b. Create BehaviorVisualization based on storage mode
                viz = None
                if behavior_storage == "rendered":
                    image_b64 = result.get("image_base64")
                    if image_b64:
                        viz = BehaviorVisualization(
                            label="Lander Trajectory",
                            media_type="image/png",
                            data_base64=image_b64,
                        )
                elif behavior_storage == "raw":
                    raw_behavior = result.get("raw_behavior")
                    if raw_behavior:
                        viz = BehaviorVisualization(
                            label="Lander Trajectory",
                            media_type="image/png",
                            raw_data=raw_behavior,
                            renderer="lunarlander_trajectory",
                        )

                # 6c. Package into BehaviorData
                if viz is not None:
                    behavior = BehaviorData(
                        observation=obs_text,
                        visualizations=[viz],
                        instance_id=str(data_path),
                    )

            return EvaluationResult(
                score=episode_reward,
                metrics=metrics,
                success=True,
                duration_ms=duration_ms,
                behavior=behavior,
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


def _subprocess_main() -> None:
    """Run a single episode in an isolated subprocess.

    Behavior depends on the ``behavior_storage`` mode from the input JSON:
    - ``"none"``:     No frame capture, fastest execution.
    - ``"raw"``:      Capture frames → composite canvas → return as raw_behavior.
    - ``"rendered"``: Capture frames → composite canvas → render to PNG →
                      return as image_base64 (avoids transferring large canvas).
    """
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
    behavior_storage = input_data.get("behavior_storage", "rendered")

    evaluator = LunarLanderPolicyEvaluatorMultimodal()

    try:
        module = evaluator._load_policy_module(policy_dir)
        if not hasattr(module, "choose_action"):
            result = {"error": "choose_action function not found in policy module"}
        else:
            capture = behavior_storage != "none"
            result = evaluator._run_episode(
                module.choose_action, seed, max_steps,
                capture_behavior=capture,
            )

            # For "rendered" mode: render in subprocess to avoid
            # transferring ~5MB canvas data over the pipe. Only the
            # ~40KB PNG is returned instead.
            if behavior_storage == "rendered" and result.get("raw_behavior"):
                raw = result["raw_behavior"]
                canvas = np.array(raw["canvas"], dtype=np.uint8)
                result["image_base64"] = _render_trajectory_image(
                    canvas, raw["reward"], raw["final_state"], raw["seed"],
                )
                del result["raw_behavior"]

    except Exception as exc:
        result = {"error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    _subprocess_main()
