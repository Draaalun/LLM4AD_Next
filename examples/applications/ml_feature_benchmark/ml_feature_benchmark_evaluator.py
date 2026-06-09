"""Evaluator for the ``ml_feature_benchmark`` example application.

Loads ``classifier.py`` from the algorithm worktree, checks feature APIs, runs
``train`` / ``predict``, and aggregates RMSE and R2 for evolution.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

from llm4ad.evaluator.base import (
    BaseEvaluator,
    EvalContext,
    EvaluationResult,
    Metric,
    MetricType,
    PythonEvaluator,
)


@BaseEvaluator.register("ml_feature_benchmark_evaluator")
class MLFeatureBenchmarkEvaluator(PythonEvaluator):
    """Evaluator for the ml_feature_benchmark task.

    Evolution is intended to change only ``fit_features`` and ``transform_features``
    inside the EVOLVE block; ``train`` / ``predict`` and KNN regressor logic stay fixed.
    """

    def __init__(self):
        """Initialize the evaluator with metric definitions."""
        self._metrics = [
            Metric(
                name="rmse",
                type=MetricType.MINIMIZE,
                weight=1.0,
                description="Root Mean Squared Error",
            ),
        ]
        self._template_dir = Path(__file__).parent / "ml_feature_algorithm"

    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return "ml_feature_benchmark_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get the list of supported metrics."""
        return self._metrics

    def _load_dataset(self, data_path: str) -> tuple:
        """Load dataset from CSV file.

        Args:
            data_path: Path to dataset file.

        Returns:
            Tuple of (features, labels).
        """
        df = pd.read_csv(data_path)
        if "SalePrice" not in df.columns:
            raise ValueError(
                f"Dataset {data_path} must contain a SalePrice column. "
                "Check evaluator.dataset.files in config.yaml."
            )
        if "Id" in df.columns:
            df = df.drop("Id", axis=1)

        y = df["SalePrice"].values.astype(float)
        x = df.drop("SalePrice", axis=1)

        # Encode categorical features
        for col in x.columns:
            if x[col].dtype == "object":
                x[col] = pd.Categorical(x[col]).codes

        x = x.apply(pd.to_numeric, errors="coerce")
        medians = x.median(numeric_only=True).fillna(0.0)
        x = x.fillna(medians)
        x = x.replace([np.inf, -np.inf], 0.0)
        x = x.values.astype(float)

        return x, y

    def _compute_rmse(self, y_true, y_pred) -> float:
        """Compute Root Mean Squared Error.

        Args:
            y_true: Ground truth values.
            y_pred: Predicted values.

        Returns:
            RMSE value.
        """
        return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    def _compute_r2(self, y_true, y_pred) -> float:
        """Compute R-squared score.

        Args:
            y_true: Ground truth values.
            y_pred: Predicted values.

        Returns:
            R2 score.
        """
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        if ss_tot == 0:
            return 0.0
        return float(1 - ss_res / ss_tot)

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """Evaluate feature extraction plus fixed KNN pipeline.

        Args:
            cfg: EvalContext

        Returns:
            Evaluation result with performance metrics.
        """
        import numpy as np

        start_time = time.time()

        try:
            features, labels = self._load_dataset(cfg.data_path)

            n_samples = len(labels)
            n_train = int(0.7 * n_samples)

            indices = np.arange(n_samples)
            np.random.seed(42)
            np.random.shuffle(indices)

            x_train = features[indices[:n_train]]
            y_train = labels[indices[:n_train]]
            x_test = features[indices[n_train:]]
            y_test = labels[indices[n_train:]]

            exec_start = time.time()

            classifier_path = Path(cfg.project_root) / "src" / "classifier.py"
            if not classifier_path.exists():
                return EvaluationResult(
                    score=0.0,
                    metrics={"score": 0.0},
                    success=False,
                    error_message=f"Classifier file not found: {classifier_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            with open(classifier_path, encoding="utf-8") as f:
                code = f.read()

            namespace = {"np": np}
            exec(code, namespace)  # noqa: S102

            required = ("fit_features", "transform_features", "train", "predict")
            missing = [n for n in required if n not in namespace]
            if missing:
                return EvaluationResult(
                    score=0.0,
                    metrics={"score": 0.0},
                    success=False,
                    error_message=f"Missing callables in classifier.py: {missing}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            train_fn = namespace["train"]
            predict_fn = namespace["predict"]

            model = train_fn(x_train, y_train)
            y_pred = predict_fn(x_test, model)

            exec_duration_ms = (time.time() - exec_start) * 1000

            if y_pred.shape != y_test.shape:
                return EvaluationResult(
                    score=0.0,
                    metrics={"score": 0.0},
                    success=False,
                    error_message=(
                        f"predict() returned shape {y_pred.shape}, expected {y_test.shape}"
                    ),
                    duration_ms=(time.time() - start_time) * 1000,
                )

            rmse = self._compute_rmse(y_test, y_pred)
            r2 = self._compute_r2(y_test, y_pred)

            metrics = {
                "rmse": rmse,
                "r2": r2,
                "execution_time_ms": exec_duration_ms,
            }

            score = self.compute_score(metrics)

            return EvaluationResult(
                score=score,
                metrics=metrics,
                success=True,
                duration_ms=exec_duration_ms,
                metadata={"dataset": cfg.data_path},
            )

        except Exception as e:
            return EvaluationResult(
                score=0.0,
                metrics={"score": 0.0},
                success=False,
                error_message=f"Evaluation error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )
