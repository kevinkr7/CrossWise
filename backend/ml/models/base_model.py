"""
ml/models/base_model.py — Abstract base class for all breeding models.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import joblib
import numpy as np


class BaseBreedingModel(ABC):
    """
    Abstract interface that every breeding model must implement.

    Sub-classes wrap one or more sklearn estimators and expose a unified
    ``fit`` / ``predict`` / ``evaluate`` / ``save`` / ``load`` API so the
    rest of the pipeline (trainer, predictor, SHAP endpoint) can remain
    model-agnostic.
    """

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @abstractmethod
    def fit(
        self,
        X_train: np.ndarray,
        y_train: dict[str, np.ndarray],
        X_val:   np.ndarray,
        y_val:   dict[str, np.ndarray],
    ) -> None:
        """Fit all internal estimators."""

    @abstractmethod
    def predict(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """
        Run inference.

        Returns a dict with at least the keys ``"yield"``,
        ``"Disease_Resistance"``, and ``"Drought_Tolerance"``.
        """

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """
        Return class probabilities for classifier targets.

        Dict keys match ``CATEGORICAL_TARGETS``.
        """

    @abstractmethod
    def get_evaluation_metrics(
        self,
        X_test: np.ndarray,
        y_test: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """Compute test-set metrics and return as a plain dict."""

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "BaseBreedingModel":
        return joblib.load(path)
