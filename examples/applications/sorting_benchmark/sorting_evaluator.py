"""Custom evaluator for C++ sorting algorithms.

This evaluator inherits from ExecutableEvaluator and handles compilation,
execution, and result parsing for sorting algorithm implementations.
"""

import platform
import re
import subprocess
import time
from pathlib import Path

from llm4ad.evaluator.base import (
    EvalContext,
    EvaluationResult,
    BaseEvaluator,
    Metric,
    MetricType,
)


@BaseEvaluator.register("sorting_evaluator")
class SortingEvaluator(BaseEvaluator):
    """Evaluator for C++ sorting algorithms.

    Compiles the provided sorting implementation, links it with the benchmark
    main program, runs it against a dataset, and parses performance metrics.
    """

    def __init__(self):
        """Initialize the sorting evaluator with configuration.

        Args:
            config: Evaluation configuration.
        """
        self._metrics = [
            Metric(
                name="execution_time_ms",
                type=MetricType.MINIMIZE,
                weight=1.0,
                description="Total execution time in milliseconds",
            )
        ]
        # Path to the C++ project template
        self._template_dir = Path(__file__).parent / "sorting_algorithm"

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return "sorting_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    def _compile(self, project_root: Path, timeout: float = 120.0) -> tuple[bool, str]:
        """Compile the C++ sorting algorithm with g++.

        On Windows, invokes g++ through MSYS2 bash (required for MSYS2 runtime).
        On macOS/Linux, calls g++ directly.

        Args:
            project_root: Path to the project root containing src/ and include/.
            timeout: Maximum time in seconds for the build process.

        Returns:
            Tuple of (success, error_message).
        """
        build_dir = project_root / "build"
        build_dir.mkdir(parents=True, exist_ok=True)

        include_dir = str(project_root / "include").replace("\\", "/")
        source_file = str(project_root / "src" / "main.cpp").replace("\\", "/")

        is_windows = platform.system() == "Windows"
        exe_name = "sorting_benchmark.exe" if is_windows else "sorting_benchmark"
        output_file = str(build_dir / exe_name).replace("\\", "/")

        flags = "-std=c++17 -O2 -DNDEBUG"
        if is_windows:
            flags += " -static"

        compile_cmd = (
            f"g++ {flags} "
            f"-I '{include_dir}' '{source_file}' -o '{output_file}'"
        )

        try:
            if is_windows:
                cmd = self._build_windows_compile_cmd(compile_cmd)
            else:
                cmd = ["bash", "-c", compile_cmd]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
            )
            if result.returncode != 0:
                return False, f"Compilation failed:\n{result.stderr}"
        except FileNotFoundError as e:
            return False, str(e)
        except subprocess.TimeoutExpired:
            return False, f"Compilation timed out after {timeout}s"

        return True, ""

    def _build_windows_compile_cmd(self, compile_cmd: str) -> list[str]:
        """Build the compile command for Windows using MSYS2 bash.

        Args:
            compile_cmd: The g++ compile command string.

        Returns:
            Command list for subprocess.run.

        Raises:
            FileNotFoundError: If MSYS2 bash is not found.
        """
        msys2_bash_candidates = [
            Path("C:/msys64/usr/bin/bash.exe"),
            Path("D:/msys64/usr/bin/bash.exe"),
        ]
        msys2_bash = None
        for p in msys2_bash_candidates:
            if p.exists():
                msys2_bash = str(p)
                break

        if msys2_bash is None:
            raise FileNotFoundError(
                "MSYS2 bash not found. Install MSYS2 and MinGW-w64 toolchain."
            )

        script = f"export PATH=/mingw64/bin:$PATH && {compile_cmd}"
        return [msys2_bash, "-lc", script]

    def _find_executable(self, build_dir: Path) -> Path | None:
        """Find the compiled executable in the build directory.

        Args:
            build_dir: The build output directory.

        Returns:
            Path to the executable, or None if not found.
        """
        candidates = [
            build_dir / "sorting_benchmark.exe",
            build_dir / "sorting_benchmark",
            build_dir / "Release" / "sorting_benchmark.exe",
            build_dir / "Debug" / "sorting_benchmark.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _parse_output(self, stdout: str, stderr: str) -> dict[str, float]:
        """Parse metrics from the benchmark executable output.

        Expects key-value lines in the format ``key: value`` from stdout.

        Args:
            stdout: Standard output from the executable.
            stderr: Standard error from the executable.

        Returns:
            Dictionary mapping metric names to parsed float values.
        """
        combined = stdout + "\n" + stderr
        result: dict[str, float] = {}
        patterns = {
            "execution_time_ms": r"execution_time_ms:\s*([\d.]+)",
            "comparisons": r"comparisons:\s*([\d.]+)",
            "swaps": r"swaps:\s*([\d.]+)",
            "correct": r"correct:\s*([\d.]+)",
        }
        for name, pattern in patterns.items():
            match = re.search(pattern, combined)
            if match:
                result[name] = float(match.group(1))
        return result

    async def evaluate(
        self,
        cfg: EvalContext
    ) -> EvaluationResult:
        """Evaluate a sorting algorithm implementation.

        Args:
            cfg: EvalContext

        Returns:
            Evaluation result with performance metrics.
        """
        start_time = time.time()

        try:
            project_root = Path(cfg.project_root)
            build_dir = project_root / "build"

            # Step 1: Compile
            compile_ok, compile_error = self._compile(project_root, timeout=cfg.timeout)
            if not compile_ok:
                return EvaluationResult(
                    score=0.0,
                    metrics={"score": 0.0},
                    success=False,
                    error_message=f"Compilation failed: {compile_error}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Step 2: Find executable
            executable_path = self._find_executable(build_dir)
            if executable_path is None:
                return EvaluationResult(
                    score=0.0,
                    metrics={"score": 0.0},
                    success=False,
                    error_message=f"Executable not found in {build_dir}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Step 3: Run the benchmark
            run_start = time.time()
            run_result = subprocess.run(
                [str(executable_path), cfg.data_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=cfg.timeout,
            )
            duration_ms = (time.time() - run_start) * 1000

            if run_result.returncode != 0:
                return EvaluationResult(
                    score=0.0,
                    metrics={"score": 0.0},
                    success=False,
                    error_message=f"Execution failed: {run_result.stderr}",
                    duration_ms=duration_ms,
                )

            # Step 4: Parse output
            metrics = self._parse_output(run_result.stdout, run_result.stderr)

            # Step 5: Check correctness
            if "correct" not in metrics or metrics["correct"] != 1.0:
                return EvaluationResult(
                    score=0.0,
                    metrics=metrics,
                    success=False,
                    error_message="Sorting result is incorrect",
                    duration_ms=duration_ms,
                )

            metrics["execution_time_ms"] = duration_ms

            # Step 6: Compute score
            score = self.compute_score(metrics)

            return EvaluationResult(
                score=score,
                metrics=metrics,
                success=True,
                duration_ms=duration_ms,
                metadata={"dataset": cfg.data_path},
            )

        except subprocess.TimeoutExpired:
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=f"Evaluation timed out after {cfg.timeout}s",
                duration_ms=cfg.timeout * 1000,
            )
        except Exception as e:
            return EvaluationResult(
                score=0.0,
                metrics={},
                success=False,
                error_message=f"Evaluation error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )
