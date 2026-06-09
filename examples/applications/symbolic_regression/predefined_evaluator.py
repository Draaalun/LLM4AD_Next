"""Symbolic Regression with Bi-Level Optimization (LLM + EC).

In this approach, the LLM explicitly defines the equation skeleton with
a `params` argument for all numeric constants/parameters. Bi-level optimization
then optimizes these predefined parameters using BFGS to minimize MSE.
"""

import concurrent.futures
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvalContext,
    EvaluationResult,
    Metric,
    MetricType,
)


@BaseEvaluator.register("predefined_bilevel_evaluator")
class PredefinedBilevelEvaluator(BaseEvaluator):
    """Auto-detecting evaluator with predefined-parameter bi-level optimization (LLM + EC).

    Automatically detects number of input variables from dataset columns.
    Supports 1-variable, 2-variable, or N-variable symbolic regression problems.
    """

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self._metrics = [
            Metric(name="mse", type=MetricType.MINIMIZE, description="Mean squared error"),
            Metric(name="rmse", type=MetricType.MINIMIZE, description="Root mean squared error"),
            Metric(name="mae", type=MetricType.MINIMIZE, description="Mean absolute error"),
        ]

    def _load_data(self, data_path: Path):
        """Load training data from file.

        Automatically detects the number of input variables from data columns.
        Format: each line contains [var1, var2, ..., varN, target]

        Returns:
            Tuple of (list of input arrays, target array)
        """
        all_inputs = None
        all_target = []

        with open(data_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    values = list(map(float, line.split()))
                    # Last column is target, rest are inputs
                    inputs = values[:-1]
                    target = values[-1]

                    if all_inputs is None:
                        all_inputs = [[] for _ in inputs]

                    for i, val in enumerate(inputs):
                        all_inputs[i].append(val)
                    all_target.append(target)

        # Convert to numpy arrays
        input_arrays = [np.array(col) for col in all_inputs]
        return input_arrays, np.array(all_target)

    @property
    def name(self) -> str:
        """Get evaluator name."""
        return "predefined_bilevel_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get supported metrics."""
        return self._metrics

    def _call_with_timeout(self, func, args: tuple, timeout_seconds: float = 5.0):
        """Call a function with timeout protection.

        Args:
            func: Function to call
            args: Arguments tuple
            timeout_seconds: Maximum execution time in seconds

        Returns:
            Function return value

        Raises:
            TimeoutError: If function exceeds timeout
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args)
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"Function execution timed out after {timeout_seconds}s")

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate the generated expression with bi-level optimization.

        Args:
            cfg: Evaluation context containing project_root and data_path

        Returns:
            Evaluation result with metrics and score
        """
        import time
        start_time = time.time()

        try:
            # Load data (auto-detects number of variables)
            inputs, target = self._load_data(Path(cfg.data_path))

            # ==========================================
            # Fix 1: Data Normalization (Z-score)
            # ==========================================
            # Normalize inputs and target to improve optimization stability
            input_means = [np.mean(x) for x in inputs]
            input_stds = [np.std(x) + 1e-8 for x in inputs]  # +1e-8 to avoid division by zero
            target_mean = np.mean(target)
            target_std = np.std(target) + 1e-8

            # Apply normalization
            normalized_inputs = [
                (x - mean) / std for x, mean, std in zip(inputs, input_means, input_stds)
            ]
            normalized_target = (target - target_mean) / target_std

            # Import the predict/equation function from the generated code
            code_root = cfg.project_root
            equation, source_code, func_param_names = self._import_equation(code_root)

            n_input_vars = len(inputs)
            n_func_params = len(func_param_names)

            # Count number of parameters by parsing params[N] usage OR tuple unpacking
            import re
            param_indices = re.findall(r'params\[(\d+)\]', source_code)
            # Also detect tuple unpacking: a, b, c, ... = params (count commas + 1)
            unpack_match = re.search(r'([^=]+)\s*=\s*params', source_code)
            unpack_count = 0
            if unpack_match:
                lhs = unpack_match.group(1)
                # Count variables on left-hand side (number of commas + 1)
                num_commas = lhs.count(',')
                if num_commas > 0:
                    unpack_count = num_commas + 1

            if param_indices:
                params_count = max(int(i) for i in param_indices) + 1
            elif unpack_count > 0:
                params_count = unpack_count
            else:
                params_count = 1  # fallback if no params found

            # Reject overly complex expressions (BFGS will diverge)
            MAX_PARAMS = 30
            if params_count > MAX_PARAMS:
                duration_ms = (time.time() - start_time) * 1000
                return EvaluationResult(
                    score=0.0,
                    metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                    success=False,
                    error_message=f"Too many parameters ({params_count}). Maximum allowed: {MAX_PARAMS}. Simplify the expression.",
                    duration_ms=duration_ms,
                )

            # ==========================================
            # Fix 2: Multi-start Random Initialization
            # Fix 3: Use normalized data for optimization
            # ==========================================
            NUM_STARTS = 15  # 15 random starting points (Feynman 2021 style)
            best_overall_mse = float('inf')
            best_overall_params = None

            # Test the equation function signature before proceeding (use normalized data)
            try:
                test_pred = self._call_with_timeout(
                    equation,
                    (*normalized_inputs, np.ones(params_count)),
                    timeout_seconds=5.0,
                )
                # Check if the result has the expected shape
                if len(test_pred) != len(target):
                    duration_ms = (time.time() - start_time) * 1000
                    return EvaluationResult(
                        score=0.0,
                        metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                        success=False,
                        error_message=f"equation function returned wrong shape: expected {len(target)}, got {len(test_pred)}",
                        duration_ms=duration_ms,
                    )
            except TimeoutError as e:
                duration_ms = (time.time() - start_time) * 1000
                return EvaluationResult(
                    score=0.0,
                    metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                    success=False,
                    error_message=f"equation function timed out: {str(e)}",
                    duration_ms=duration_ms,
                )
            except TypeError as e:
                duration_ms = (time.time() - start_time) * 1000
                error_str = str(e)
                # Provide detailed debugging info for signature mismatches
                error_msg = (
                    f"Signature mismatch! Data has {n_input_vars} input vars, "
                    f"function expects {n_func_params} params: {func_param_names}. "
                    f"Error: {error_str}"
                )
                # Check if this is likely a variable count mismatch (template not updated)
                if "missing" in error_str.lower() and "argument" in error_str.lower():
                    error_msg = (
                        f"VARIABLE COUNT MISMATCH! Data has {n_input_vars} input variable(s) "
                        f"but equation({', '.join(func_param_names)}) expects {n_func_params}. "
                        f"Did you forget to commit sr_algorithm/model.py changes? "
                        f"Details: {error_str}"
                    )
                return EvaluationResult(
                    score=0.0,
                    metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                    success=False,
                    error_message=error_msg,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return EvaluationResult(
                    score=0.0,
                    metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                    success=False,
                    error_message=f"equation function test call failed: {str(e)}",
                    duration_ms=duration_ms,
                )

            # Define loss function with NaN protection (uses normalized data)
            def loss_function(params):
                try:
                    y_pred = equation(*normalized_inputs, params)
                    # Check for NaN or Inf in predictions
                    if np.any(np.isnan(y_pred)) or np.any(np.isinf(y_pred)):
                        return 1e10
                    # Use Huber loss (more robust than MSE)
                    error = y_pred - normalized_target
                    huber_loss = np.mean(np.where(np.abs(error) < 1.0, 0.5 * error**2, np.abs(error) - 0.5))
                    return huber_loss
                except TypeError as e:
                    raise TypeError(f"equation function signature error: {str(e)}") from e
                except Exception:
                    return 1e10

            # ==========================================
            # Fix 4: Multi-start optimization loop
            # Fix 5: More iterations + L-BFGS-B (better than BFGS)
            # ==========================================
            def _run_optimization():
                """Run multi-start optimization in a separate thread for timeout."""
                best_mse = float('inf')
                best_params = None

                for start_idx in range(NUM_STARTS):
                    # Random initialization in [-3, 3] range (not just 1.0!)
                    initial_guess = np.random.uniform(-3.0, 3.0, params_count)

                    # Strategy 1: L-BFGS-B (bounded, more robust than BFGS)
                    try:
                        result = minimize(
                            loss_function, initial_guess, method='L-BFGS-B',
                            options={'maxiter': 1000, 'ftol': 1e-9, 'gtol': 1e-8}
                        )
                        if result.fun < best_mse and not np.isnan(result.fun):
                            best_mse = result.fun
                            best_params = result.x.copy()
                    except Exception:
                        pass

                    # Strategy 2: Nelder-Mead (global search)
                    try:
                        result = minimize(
                            loss_function, initial_guess, method='Nelder-Mead',
                            options={'maxiter': 500, 'xatol': 1e-8, 'fatol': 1e-8}
                        )
                        if result.fun < best_mse and not np.isnan(result.fun):
                            best_mse = result.fun
                            best_params = result.x.copy()
                    except Exception:
                        pass

                return best_mse, best_params

            # Run entire optimization loop with timeout
            try:
                best_overall_mse, best_overall_params = self._call_with_timeout(
                    _run_optimization,
                    (),
                    timeout_seconds=60.0,  # 60s total for all optimization
                )
            except TimeoutError as e:
                duration_ms = (time.time() - start_time) * 1000
                return EvaluationResult(
                    score=0.0,
                    metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                    success=False,
                    error_message=f"Optimization loop timed out: {str(e)}",
                    duration_ms=duration_ms,
                )

            # If all optimization strategies failed, return zero score
            if best_overall_params is None:
                duration_ms = (time.time() - start_time) * 1000
                return EvaluationResult(
                    score=0.0,
                    metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                    success=False,
                    error_message="All optimization strategies failed",
                    duration_ms=duration_ms,
                )

            # ==========================================
            # Denormalize for final metric calculation
            # ==========================================
            optimized_params = best_overall_params
            y_pred_normalized = equation(*normalized_inputs, optimized_params)

            # Denormalize predictions back to original scale
            y_pred = y_pred_normalized * target_std + target_mean

            # Check for NaN in final predictions
            if np.any(np.isnan(y_pred)) or np.any(np.isinf(y_pred)):
                duration_ms = (time.time() - start_time) * 1000
                return EvaluationResult(
                    score=0.0,
                    metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                    success=False,
                    error_message="Final predictions contain NaN or Inf",
                    duration_ms=duration_ms,
                )

            # Calculate final metrics on original scale
            final_mse = np.mean((y_pred - target) ** 2)
            final_rmse = np.sqrt(final_mse)
            final_mae = np.mean(np.abs(y_pred - target))

            # Parameter count penalty: encourage simpler expressions with fewer params
            param_penalty = params_count * 0.001  # 0.1% MSE increase penalty per parameter
            penalized_mse = final_mse * (1 + param_penalty)

            # Save optimized parameters to file for inspection
            try:
                with open(f"{code_root}/optimized_params.json", 'w') as f:
                    json.dump({
                        'optimized_params': optimized_params.tolist(),
                        'final_mse': float(final_mse),
                        'num_random_restarts': NUM_STARTS,
                    }, f, indent=2)
            except Exception:
                pass

            duration_ms = (time.time() - start_time) * 1000

            # Compute the overall score using -log10(mse)
            # This creates a more discernible fitness landscape:
            # - MSE 1e-2 → score = 2
            # - MSE 1e-4 → score = 4
            # - MSE 1e-6 → score = 6
            # Makes differences between good solutions more visible to evolution
            metrics_dict = {
                'mse': final_mse,
                'rmse': final_rmse,
                'mae': final_mae,
                'penalized_mse': penalized_mse,
                'params_count': params_count,
            }
            score = -math.log10(penalized_mse + 1e-12)  # +epsilon to prevent log(0)

            return EvaluationResult(
                score=score,
                metrics=metrics_dict,
                success=True,
                duration_ms=duration_ms,
            )
        except TypeError as e:
            # Catch TypeError from loss_function (signature errors)
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            if "params" in error_msg.lower() or "signature" in error_msg.lower():
                error_msg = f"equation function signature error: {error_msg}"
            return EvaluationResult(
                score=0.0,
                metrics={'mse': float('inf'), 'rmse': float('inf'), 'mae': float('inf')},
                success=False,
                error_message=error_msg,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
            )

    def _import_equation(self, code_root: str):
        """Import the equation function from the generated model.py.

        Returns:
            Tuple of (function, source_code)

        Raises:
            TypeError: If the equation function is missing the params argument.
            ValueError: If no equation or predict function is found.
        """
        import importlib.util
        import inspect
        import sys

        spec = importlib.util.spec_from_file_location(
            "model",
            f"{code_root}/model.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["model"] = module
        spec.loader.exec_module(module)

        # Look for either 'equation' or 'predict' function
        if hasattr(module, 'equation'):
            func = module.equation
        elif hasattr(module, 'predict'):
            func = module.predict
        else:
            raise ValueError("Could not find 'equation' or 'predict' function in generated code")

        # Check function signature for params argument
        sig = inspect.signature(func)
        params_names = list(sig.parameters.keys())

        # Check if there is an explicit 'params' parameter
        has_params_param = 'params' in params_names

        # Check if the function accepts *args or **kwargs
        has_varargs = any(
            p.kind == inspect.Parameter.VAR_POSITIONAL or
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )

        # Also check if the function has at least enough parameters to accept inputs + params
        # For N input variables, we need at least N parameters plus the params argument
        # We'll detect the actual number of input variables when the function is called
        # For now, we just check if there's any way to pass params

        if not has_params_param and not has_varargs:
            # No way to pass params - this is a signature error
            raise TypeError(
                f"equation function missing 'params' argument. "
                f"Found signature: {sig}. "
                f"Expected: equation(*inputs, params) or equation(..., params=...)"
            )

        original_func = func
        original_param_names = params_names  # Keep original params for error messages

        def safe_equation(*args, **kwargs):
            """Wrapper that adds NaN protection to the equation function."""
            try:
                # Check if the function expects a params argument
                if has_params_param:
                    # Call normally with params as a named or positional argument
                    result = original_func(*args, **kwargs)
                else:
                    # Function accepts *args or **kwargs, try to call with all arguments
                    result = original_func(*args, **kwargs)

                # Replace NaN and Inf with large finite numbers
                result = np.where(np.isnan(result), 1e10, result)
                result = np.where(np.isinf(result), 1e10 * np.sign(result), result)
                return result
            except TypeError as e:
                # Re-raise with clear message about signature
                raise TypeError(f"equation function signature error: {str(e)}") from e
            except Exception:
                # Return a large penalty value if the equation fails
                if args and len(args) > 0:
                    try:
                        return np.full_like(args[0], 1e10)
                    except Exception:
                        return np.array([1e10])
                return np.array([1e10])

        return safe_equation, inspect.getsource(original_func), original_param_names