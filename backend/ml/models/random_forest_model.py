"""
ml/models/random_forest_model.py — Random Forest breeding model.

Wraps estimators dynamically based on config:
  * ``RandomForestRegressor``  → Yield_t_ha (continuous)
  * ``RandomForestClassifier`` → (N categorical targets like Disease, Drought, Quality, etc.)

All are trained with ``oob_score=True`` so we get an out-of-bag
quality estimate at no extra cost.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, r2_score

from ml.models.base_model import BaseBreedingModel
from config import CATEGORICAL_TARGETS

logger = logging.getLogger(__name__)


class RandomForestBreedingModel(BaseBreedingModel):
    """
    Multi-output Random Forest breeding model.

    One regressor for yield and a dictionary of classifiers for categorical traits.
    All estimators share the same hyperparameters
    (n_estimators, max_depth, random_state, n_jobs).
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int | None = None,
        min_samples_leaf: int = 1,
        random_state: int = 42,
        n_jobs: int = -1,
    ) -> None:
        """
        Parameters
        ----------
        n_estimators : int
            Number of trees in the forest.
        max_depth : int | None
            Maximum depth of the trees.
        min_samples_leaf : int
            Minimum number of samples required to be at a leaf node.
        random_state : int
            Random seed for reproducibility.
        n_jobs : int
            Number of parallel jobs to run.
        """
        super().__init__()
        self.n_estimators = n_estimators
        self.max_depth    = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.n_jobs       = n_jobs

        self.regressor:      RandomForestRegressor  | None = None
        self.classifiers:    dict[str, RandomForestClassifier] = {}
        self._oob_scores:    dict[str, float] = {}
        self.feature_importances_: np.ndarray | None = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_regressor(self) -> RandomForestRegressor:
        return RandomForestRegressor(
            n_estimators = self.n_estimators,
            max_depth    = self.max_depth,
            min_samples_leaf = self.min_samples_leaf,
            oob_score    = True,
            n_jobs       = self.n_jobs,
            random_state = self.random_state,
        )

    def _make_classifier(self) -> CalibratedClassifierCV:
        rf = RandomForestClassifier(
            n_estimators = self.n_estimators,
            max_depth    = self.max_depth,
            min_samples_leaf = self.min_samples_leaf,
            n_jobs       = self.n_jobs,
            random_state = self.random_state,
        )
        # Using sigmoid calibration to get better probabilities
        return CalibratedClassifierCV(rf, method='sigmoid', cv=3)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def fit(
        self,
        X_train: np.ndarray,
        y_train: dict[str, np.ndarray],
        X_val:   np.ndarray,
        y_val:   dict[str, np.ndarray],
    ) -> None:
        """Train all estimators. Validation split is used only for logging."""

        # ── Yield regressor ───────────────────────────────────────────────────
        if "yield" in y_train:
            logger.info("Fitting yield regressor …")
            self.regressor = self._make_regressor()
            self.regressor.fit(X_train, y_train["yield"])
            self._oob_scores["yield_oob"] = float(self.regressor.oob_score_)
            self.feature_importances_ = self.regressor.feature_importances_
            val_r2 = float(r2_score(y_val["yield"], self.regressor.predict(X_val)))
            logger.info("Yield R² (val) = %.4f | OOB = %.4f", val_r2, self._oob_scores["yield_oob"])

        # ── Categorical classifiers ───────────────────────────────────────────
        for target in CATEGORICAL_TARGETS:
            if target in y_train:
                logger.info(f"Fitting {target} classifier …")
                clf = self._make_classifier()
                clf.fit(X_train, y_train[target])
                self.classifiers[target] = clf
                # CalibratedClassifierCV doesn't have oob_score_
                oob_key = f"{target.lower()}_oob"
                self._oob_scores[oob_key] = 0.0
                val_acc = float(accuracy_score(y_val[target], clf.predict(X_val)))
                logger.info(f"{target} accuracy (val) = %.4f", val_acc)

    def predict(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """Run inference and return raw prediction arrays (not decoded yet)."""
        out: dict[str, np.ndarray] = {}
        if self.regressor is not None:
            out["yield"] = self.regressor.predict(X)
        for target, clf in self.classifiers.items():
            out[target] = clf.predict(X)
        return out

    def predict_proba(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """Return class probability arrays for classifiers."""
        out: dict[str, np.ndarray] = {}
        for target, clf in self.classifiers.items():
            out[target] = clf.predict_proba(X)
        return out

    def get_evaluation_metrics(
        self,
        X_test: np.ndarray,
        y_test: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """Compute held-out test-set metrics."""
        metrics: dict[str, Any] = {}
        metrics.update(self._oob_scores)

        if self.regressor is not None and "yield" in y_test:
            y_pred_yield = self.regressor.predict(X_test)
            metrics["yield_r2"]   = round(float(r2_score(y_test["yield"], y_pred_yield)), 4)
            metrics["yield_rmse"] = round(
                float(np.sqrt(np.mean((y_test["yield"] - y_pred_yield) ** 2))), 4
            )

        for target, clf in self.classifiers.items():
            if target in y_test:
                acc = accuracy_score(y_test[target], clf.predict(X_test))
                metrics[f"{target.lower()}_accuracy"] = round(float(acc), 4)

        return metrics
