"""Feature extraction benchmark: evolve ``fit_features`` / ``transform_features`` only.

The downstream regressor is fixed: XGBoost (XGBRegressor).
Only the feature functions inside the EVOLVE block are evolved.
"""

from __future__ import annotations

import numpy as np


# EVOLVE_START
def fit_features(x_train: np.ndarray, y_train: np.ndarray):
    """Learn feature-extraction state from training data only.

    Reproduces the comprehensive data exploration logic from the notebook:
    ``comprehensive-data-exploration-with-python.ipynb``.
    Steps (mirroring the notebook flow):
      1. Missing data handling  (drop columns with >15%% missing)
      2. Outlier detection      (GrLivArea top-2 extreme values)
      3. Normality / log-transform  (GrLivArea, TotalBsmtSF)
      4. Create HasBsmt indicator
      5. Correlation-based feature selection (top-k)
      6. Standardisation

    Args:
        x_train: Training inputs, shape (n_samples, n_features).
        y_train: Training targets, shape (n_samples,), continuous values (house prices).

    Returns:
        State object passed to ``transform_features``.
    """
    x_train = np.asarray(x_train, dtype=float)
    x_train = np.nan_to_num(x_train, nan=0.0, posinf=0.0, neginf=0.0)
    y_train = np.asarray(y_train, dtype=float)
    y_train = np.nan_to_num(y_train, nan=0.0, posinf=0.0, neginf=0.0)
    n_samples, n_features = x_train.shape

    # ------------------------------------------------------------------
    # 1. MISSING DATA  (notebook section 4)
    #    Delete columns with >15% missing values.
    #    In the raw Kaggle CSV these are:
    #      PoolQC, MiscFeature, Alley, Fence, FireplaceQu
    #    plus the Garage*X* group and Bsmt*X* group (all same count).
    #    Since the evaluator already label-encodes categoricals and fills
    #    numeric NA with median, the only remaining "sentinel" for
    #    originally-missing categoricals is the code for NA (usually -1).
    #    We detect columns where >15% of rows still carry that sentinel.
    # ------------------------------------------------------------------
    na_code = -1.0                     # label-encoded NA from evaluator
    na_threshold = 0.15 * n_samples    # 15% missing threshold
    drop_cols = set()

    for j in range(n_features):
        if np.sum(x_train[:, j] == na_code) > na_threshold:
            drop_cols.add(j)

    # Also drop the Garage*X* and Bsmt*X* groups when any member is dropped
    # (mirrors notebook logic: "same number of missing data").
    garage_cols = {57, 58, 59, 62, 63}   # GarageType, YrBlt, Finish, Qual, Cond
    bsmt_cols = {29, 30, 31, 32, 34}     # BsmtQual, Cond, Exposure, FinType1, FinType2
    masvnr_cols = {24, 25}               # MasVnrType, MasVnrArea

    if any(c in drop_cols for c in garage_cols):
        drop_cols.update(garage_cols)
    if any(c in drop_cols for c in bsmt_cols):
        drop_cols.update(bsmt_cols)
    if any(c in drop_cols for c in masvnr_cols):
        drop_cols.update(masvnr_cols)

    keep_cols = [j for j in range(n_features) if j not in drop_cols]
    keep_mask = np.zeros(n_features, dtype=bool)
    keep_mask[keep_cols] = True
    x_clean = x_train[:, keep_cols]

    # ------------------------------------------------------------------
    # 2. OUTLIERS  (notebook section "Out liars!")
    #    Notebook deletes the two largest GrLivArea observations
    #    (Ids 1299 and 524).  We cannot delete rows from the test set,
    #    but we *can* remember the GrLivArea threshold and cap future
    #    values at that level.
    # ------------------------------------------------------------------
    # Map original GrLivArea column index to position in kept columns
    grlivarea_orig = 45
    grlivarea_pos = None
    if grlivarea_orig in keep_cols:
        grlivarea_pos = keep_cols.index(grlivarea_orig)
        col_data = x_clean[:, grlivarea_pos]
        # Threshold = 2nd-largest value (delete the single max)
        sorted_vals = np.sort(col_data)
        grlivarea_threshold = float(sorted_vals[-2]) if len(sorted_vals) >= 2 else float(sorted_vals[-1])
    else:
        grlivarea_threshold = None

    # ------------------------------------------------------------------
    # 3. LOG TRANSFORMS  (notebook sections 5 / "In the search for normality")
    #    GrLivArea -> log(GrLivArea)
    #    TotalBsmtSF -> 0 if 0, else log(TotalBsmtSF)
    # ------------------------------------------------------------------
    totalbsmt_orig = 37
    totalbsmt_pos = None
    if totalbsmt_orig in keep_cols:
        totalbsmt_pos = keep_cols.index(totalbsmt_orig)

    # Learn means / stds on the log-transformed training data
    x_proc = x_clean.copy()

    if grlivarea_pos is not None:
        # Cap outliers first, then log. Guard against negative values produced
        # by malformed generated candidates or unusual datasets.
        x_proc[:, grlivarea_pos] = np.minimum(x_proc[:, grlivarea_pos], grlivarea_threshold)
        x_proc[:, grlivarea_pos] = np.log1p(np.clip(x_proc[:, grlivarea_pos], 0.0, None))

    if totalbsmt_pos is not None:
        col = x_proc[:, totalbsmt_pos]
        col_logged = np.where(col > 0, np.log1p(col), 0.0)
        # Replace the original column with the logged version
        x_proc[:, totalbsmt_pos] = col_logged

    # ------------------------------------------------------------------
    # 4. HASBSMT INDICATOR  (notebook cell 71)
    #    Append a binary column: 1 if TotalBsmtSF > 0 else 0.
    #    We store the index where it should be appended.
    # ------------------------------------------------------------------
    hasbsmt_data = None
    if totalbsmt_pos is not None:
        hasbsmt_data = (x_clean[:, totalbsmt_pos] > 0).astype(float)
        x_proc = np.column_stack([x_proc, hasbsmt_data])
        hasbsmt_pos = x_proc.shape[1] - 1
    else:
        hasbsmt_pos = None

    x_proc = np.nan_to_num(x_proc, nan=0.0, posinf=0.0, neginf=0.0)

    # ------------------------------------------------------------------
    # 5. CORRELATION-BASED FEATURE SELECTION
    #    Keep top 50%% by |correlation| with y_train (at least 10).
    # ------------------------------------------------------------------
    n_proc = x_proc.shape[1]
    correlations = np.zeros(n_proc)
    for j in range(n_proc):
        col = x_proc[:, j]
        if np.std(col) == 0 or np.std(y_train) == 0:
            correlations[j] = 0.0
            continue
        corr = np.corrcoef(col, y_train)[0, 1]
        correlations[j] = abs(corr) if np.isfinite(corr) else 0.0

    top_k = max(10, int(n_proc * 0.5))
    top_indices = np.argsort(correlations)[::-1][:top_k]
    select_mask = np.zeros(n_proc, dtype=bool)
    select_mask[top_indices] = True
    if not np.any(select_mask):
        select_mask = np.ones(n_proc, dtype=bool)

    x_selected = x_proc[:, select_mask]

    # ------------------------------------------------------------------
    # 6. STANDARDISATION
    # ------------------------------------------------------------------
    mean = np.mean(x_selected, axis=0)
    std = np.std(x_selected, axis=0)
    std_safe = np.where(std == 0, 1.0, std)
    x_std = (x_selected - mean) / std_safe
    x_std = np.nan_to_num(x_std, nan=0.0, posinf=0.0, neginf=0.0)

    # ------------------------------------------------------------------
    # 7. PCA (lightweight, same spirit as original benchmark)
    #    Keep enough components to explain 95%% variance.
    # ------------------------------------------------------------------
    n_samples_post, n_features_post = x_std.shape
    if n_features_post > 0 and n_samples_post > 1:
        try:
            cov = np.cov(x_std, rowvar=False)
            cov = np.atleast_2d(np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0))
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            idx = np.argsort(eigenvalues)[::-1]
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]

            total_var = np.sum(np.maximum(eigenvalues, 0.0))
            if total_var > 0:
                cum_var = np.cumsum(np.maximum(eigenvalues, 0.0)) / total_var
                n_components = int(np.searchsorted(cum_var, 0.95) + 1)
                n_components = min(n_components, n_features_post)
            else:
                n_components = n_features_post
        except np.linalg.LinAlgError:
            n_components = n_features_post
            eigenvectors = np.eye(n_features_post)
    else:
        n_components = max(1, n_features_post)
        eigenvectors = np.eye(n_features_post)

    projection = eigenvectors[:, :n_components]

    return {
        "keep_mask": keep_mask,
        "grlivarea_pos": grlivarea_pos,
        "grlivarea_threshold": grlivarea_threshold,
        "totalbsmt_pos": totalbsmt_pos,
        "hasbsmt_pos": hasbsmt_pos,
        "select_mask": select_mask,
        "mean": mean,
        "std": std_safe,
        "projection": projection,
    }


def transform_features(x: np.ndarray, state) -> np.ndarray:
    """Map raw inputs to features used by the fixed regressor.

    Applies the exact same transformations learned in ``fit_features``:
    column dropping, outlier capping, log transforms, HasBsmt append,
    feature selection, standardisation, PCA projection.

    Args:
        x: Array of shape (n_samples, n_features).
        state: Object returned by ``fit_features``.

    Returns:
        2D float array of shape (n_samples, n_features_out) with finite values.
    """
    x = np.asarray(x, dtype=float)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    if state is None:
        return x.copy()

    keep_mask = state["keep_mask"]
    grlivarea_pos = state["grlivarea_pos"]
    grlivarea_threshold = state["grlivarea_threshold"]
    totalbsmt_pos = state["totalbsmt_pos"]
    hasbsmt_pos = state["hasbsmt_pos"]
    select_mask = state["select_mask"]
    mean = state["mean"]
    std = state["std"]
    projection = state["projection"]

    # 1. Drop columns
    x_clean = x[:, keep_mask]

    # 2. Outlier cap + log transform for GrLivArea
    if grlivarea_pos is not None and grlivarea_threshold is not None:
        x_clean[:, grlivarea_pos] = np.minimum(
            x_clean[:, grlivarea_pos], grlivarea_threshold
        )
        x_clean[:, grlivarea_pos] = np.log1p(
            np.clip(x_clean[:, grlivarea_pos], 0.0, None)
        )

    # 3. TotalBsmtSF special log handling
    if totalbsmt_pos is not None:
        col = x_clean[:, totalbsmt_pos]
        x_clean[:, totalbsmt_pos] = np.where(col > 0, np.log1p(col), 0.0)

    # 4. Append HasBsmt
    if hasbsmt_pos is not None and totalbsmt_pos is not None:
        hasbsmt = (x_clean[:, totalbsmt_pos] > 0).astype(float)
        x_clean = np.column_stack([x_clean, hasbsmt])

    # 5. Feature selection
    x_selected = x_clean[:, select_mask]
    x_selected = np.nan_to_num(x_selected, nan=0.0, posinf=0.0, neginf=0.0)

    # 6. Standardise
    x_std = (x_selected - mean) / std
    x_std = np.nan_to_num(x_std, nan=0.0, posinf=0.0, neginf=0.0)

    # 7. Project
    x_proj = x_std @ projection
    return np.nan_to_num(x_proj, nan=0.0, posinf=0.0, neginf=0.0)


# EVOLVE_END


def train(x_train: np.ndarray, y_train: np.ndarray) -> dict:
    """Fit features on raw training data, then fit fixed regressor on transformed features."""
    feat_state = fit_features(x_train, y_train)
    x_tr = transform_features(x_train, feat_state)
    x_tr = np.asarray(x_tr, dtype=float)
    if x_tr.ndim != 2:
        raise ValueError("transform_features must return a 2D array")
    if x_tr.shape[0] != x_train.shape[0]:
        raise ValueError("transform_features must preserve number of rows")
    if not np.all(np.isfinite(x_tr)):
        raise ValueError("transform_features must return finite values")

    y_train = np.asarray(y_train, dtype=float)

    import xgboost as xgb  # type: ignore

    reg = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        min_child_weight=1.0,
        random_state=42,
        n_jobs=1,
        tree_method="hist",
        objective="reg:squarederror",
    )
    reg.fit(x_tr, y_train)
    return {
        "backend": "xgb",
        "model": reg,
        "feature_state": feat_state,
    }


def predict(x_test: np.ndarray, model: dict) -> np.ndarray:
    """Transform test inputs with training state, then predict continuous values."""
    feat_state = model["feature_state"]
    x_te = transform_features(x_test, feat_state)
    x_te = np.asarray(x_te, dtype=float)
    if x_te.ndim != 2:
        raise ValueError("transform_features must return a 2D array")
    if x_te.shape[0] != x_test.shape[0]:
        raise ValueError("transform_features must preserve number of rows")
    if not np.all(np.isfinite(x_te)):
        raise ValueError("transform_features must return finite values")

    reg = model["model"]
    return reg.predict(x_te).astype(float)
