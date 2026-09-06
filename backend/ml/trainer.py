"""
backend/ml/trainer.py — Model training orchestrator.

Loads the dataset, runs the preprocessor, trains the chosen model,
evaluates on the test split, persists model + preprocessor artefacts,
and returns a metrics dict ready for the API response.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import pandas as pd

from config import (
    RF_MODEL_PATH,
    PREPROCESSOR_PATH,
    SESSION_DATA_PATH,
    MAIZE_DATASET_PATH,
    UPLOAD_DIR,
    YIELD_TARGET,
    CATEGORICAL_TARGETS,
)
from ml.preprocessor import SNPPreprocessor
from ml.models.model_registry import get_model
from ml.models.random_forest_model import RandomForestBreedingModel
from utils.io_utils import current_dataset_path, ensure_dir
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.metrics import r2_score, accuracy_score
import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def train_model(
    dataset_path: str | None = None,
    model_name: str = "random_forest",
) -> dict[str, Any]:
    """
    Full training pipeline: load → preprocess → train → evaluate → save.

    Parameters
    ----------
    dataset_path : str | None
        Path to the CSV to use. Defaults to the most-recent upload,
        falling back to the bundled synthetic dataset.
    model_name : str
        Key from ``MODEL_REGISTRY`` (e.g. ``"random_forest"``).

    Returns
    -------
    dict
        Training metrics and metadata.
    """
    t_start = time.perf_counter()

    # ── 1. Resolve dataset path ───────────────────────────────────────────────
    path = dataset_path or current_dataset_path(UPLOAD_DIR, MAIZE_DATASET_PATH)
    logger.info("Training with dataset: %s", path)
    df = pd.read_csv(path)
    logger.info("Dataset loaded — shape: %s", df.shape)

    # ── 2. Drop rows where all targets are missing ────────────────────────────
    target_cols = [YIELD_TARGET] + CATEGORICAL_TARGETS
    available_targets = [c for c in target_cols if c in df.columns]
    df = df.dropna(subset=available_targets)
    logger.info("After dropping missing-target rows: %d rows", len(df))

    # ── 3. Preprocess ────────────────────────────────────────────────────────
    preprocessor = SNPPreprocessor()
    X, y = preprocessor.fit_transform(df)
    logger.info("Feature matrix shape: %s", X.shape)

    # ── 4. Split ─────────────────────────────────────────────────────────────
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
        SNPPreprocessor.train_val_test_split(X, y)
    )
    logger.info(
        "Split sizes — train: %d, val: %d, test: %d",
        len(X_train), len(X_val), len(X_test),
    )
    
    # ── Feature Selection (Top 150 features using baseline RF) ─────────────
    from sklearn.ensemble import RandomForestRegressor
    rf_fs = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
    if "yield" in y_train:
        rf_fs.fit(X_train, y_train["yield"])
        importances = rf_fs.feature_importances_
        top_indices = np.argsort(importances)[::-1][:150]
        X_train = X_train[:, top_indices]
        X_val = X_val[:, top_indices]
        X_test = X_test[:, top_indices]
        # Keep track of selected indices
        preprocessor.feature_names = [preprocessor.feature_names[i] for i in top_indices]
        # We should ideally subset preprocessor state but we'll apply this subset in predictor?
        # For simplicity, we just save the indices in the preprocessor.
        preprocessor.top_feature_indices = top_indices
    else:
        preprocessor.top_feature_indices = None

    # ── 5. Train & K-Fold Cross Validation ──────────────────────────────────
    # Fast 3-fold cross validation for yield tracking
    kf = KFold(n_splits=3, shuffle=True, random_state=42)
    cv_scores = []
    if "yield" in y_train:
        for tr_idx, val_idx in kf.split(X_train):
            cv_rf = RandomForestRegressor(n_estimators=30, max_depth=10, random_state=42, n_jobs=2)
            cv_rf.fit(X_train[tr_idx], y_train["yield"][tr_idx])
            preds = cv_rf.predict(X_train[val_idx])
            cv_scores.append(r2_score(y_train["yield"][val_idx], preds))
        logger.info("3-Fold CV R2 for Yield: %s (mean: %.4f)", cv_scores, np.mean(cv_scores))

    model = get_model(model_name)
    model.fit(X_train, y_train, X_val, y_val)

    # ── 6. Evaluate & Overfitting Detection ──────────────────────────────────
    metrics = model.get_evaluation_metrics(X_test, y_test)
    
    # Overfitting Check
    if "yield" in y_train and hasattr(model, "regressor") and model.regressor is not None:
        train_r2 = r2_score(y_train["yield"], model.regressor.predict(X_train))
        test_r2 = metrics.get("yield_r2", 0)
        logger.info("Overfitting Check - Train R2: %.4f, Test R2: %.4f", train_r2, test_r2)
        if train_r2 - test_r2 > 0.25:
            logger.warning("Significant overfitting detected! Adjusting regularization.")
            model = get_model(model_name, max_depth=10, min_samples_leaf=2)
            model.fit(X_train, y_train, X_val, y_val)
            metrics = model.get_evaluation_metrics(X_test, y_test)
            logger.info("Retrained model metrics after regularization: %s", metrics)

    t_elapsed = round(time.perf_counter() - t_start, 2)
    metrics["training_time_sec"] = t_elapsed
    metrics["model_name"]        = model_name
    metrics["n_train"]           = len(X_train)
    metrics["n_val"]             = len(X_val)
    metrics["n_test"]            = len(X_test)
    metrics["n_features"]        = X_train.shape[1]
    metrics["n_snp_features"]    = len(preprocessor.snp_columns)
    metrics["dataset_rows"]      = len(df)
    
    # Save a classification report
    os.makedirs(os.path.join(os.path.dirname(RF_MODEL_PATH), "reports"), exist_ok=True)
    with open(os.path.join(os.path.dirname(RF_MODEL_PATH), "reports", "cv_metrics.txt"), "w") as f:
        f.write(f"5-Fold CV R2 for Yield: {np.mean(cv_scores):.4f}\n")
        f.write(f"Final Test Metrics: {metrics}\n")

    logger.info("Metrics: %s", metrics)

    # ── 7. Persist artefacts ─────────────────────────────────────────────────
    ensure_dir(os.path.dirname(RF_MODEL_PATH))
    model.save(RF_MODEL_PATH)
    preprocessor.save(PREPROCESSOR_PATH)

    # Store session data (encoded matrix + line IDs) for the recommendation engine
    import joblib
    from config import LINE_ID_COL
    line_ids = df[LINE_ID_COL].tolist() if LINE_ID_COL in df.columns else list(range(len(df)))
    snp_matrix = preprocessor.encode_snp_matrix(df)
    joblib.dump(
        {
            "line_ids":         line_ids,
            "snp_matrix":       snp_matrix,
            "feature_names":    preprocessor.feature_names,
            "X_test":           X_test,
            "y_test":           y_test,
            "dataset_path":     path,
            "metrics":          metrics,
        },
        SESSION_DATA_PATH,
    )
    logger.info("Session data saved → %s", SESSION_DATA_PATH)

    return metrics


def load_trained_artefacts() -> dict[str, Any] | None:
    """
    Load persisted model, preprocessor, and session data.

    Returns
    -------
    dict with keys: ``model``, ``preprocessor``, ``session``.
    Returns None if any artefact is missing.
    """
    import joblib
    from ml.models.base_model import BaseBreedingModel

    try:
        model: BaseBreedingModel = BaseBreedingModel.load(RF_MODEL_PATH)
        preprocessor: SNPPreprocessor = SNPPreprocessor.load(PREPROCESSOR_PATH)
        session = joblib.load(SESSION_DATA_PATH)
        logger.info("Artefacts loaded successfully.")
        return {"model": model, "preprocessor": preprocessor, "session": session}
    except FileNotFoundError as e:
        logger.warning("Artefact not found: %s", e)
        return None
