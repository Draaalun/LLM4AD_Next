"""Hyperparameter benchmark: evolve HYPERPARAMS only for a fixed XGBRegressor.

The downstream regressor is fixed: XGBoost XGBRegressor.
Only the hyperparameter values inside the EVOLVE block are modified by search.
"""

from __future__ import annotations

import numpy as np

# EVOLVE_START
HYPERPARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "reg_lambda": 1.0,
    "min_child_weight": 1.0,
    "gamma": 0.0,
}
# EVOLVE_END


def train(x_train: np.ndarray, y_train: np.ndarray) -> dict:
    """Fit fixed XGBRegressor with evolved hyperparameters.

    Args:
        x_train: Training features, shape (n_samples, n_features).
        y_train: Training targets, shape (n_samples,), continuous values.

    Returns:
        Model dict with fitted XGBRegressor.
    """
    import xgboost as xgb  # type: ignore

    hp = HYPERPARAMS
    reg = xgb.XGBRegressor(
        n_estimators=int(max(1, hp["n_estimators"])),
        max_depth=int(max(1, hp["max_depth"])),
        learning_rate=float(max(0.001, hp["learning_rate"])),
        subsample=float(np.clip(hp["subsample"], 0.1, 1.0)),
        colsample_bytree=float(np.clip(hp["colsample_bytree"], 0.1, 1.0)),
        reg_lambda=float(max(0.0, hp["reg_lambda"])),
        min_child_weight=float(max(0.0, hp["min_child_weight"])),
        gamma=float(max(0.0, hp["gamma"])),
        random_state=42,
        n_jobs=1,
        tree_method="hist",
        objective="reg:squarederror",
    )
    reg.fit(x_train, y_train)
    return {"model": reg}


def predict(x_test: np.ndarray, model: dict) -> np.ndarray:
    """Predict continuous values with the fitted XGBRegressor.

    Args:
        x_test: Test features, shape (n_samples, n_features).
        model: Dict from ``train()`` with fitted model.

    Returns:
        Predicted values, shape (n_samples,), float.
    """
    reg = model["model"]
    return reg.predict(x_test).astype(float)
