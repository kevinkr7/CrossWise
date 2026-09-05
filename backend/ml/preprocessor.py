"""
ml/preprocessor.py — SNP genotype + environmental feature preprocessor.

Responsibilities
----------------
- Detect SNP columns (prefix ``SNP_``) and encode allele pairs → 0 / 1 / 2
  (minor-allele dosage) with mode imputation for missing "NN" calls.
- Detect and normalise environmental feature columns.
- Label-encode categorical target columns.
- Expose ``fit_transform``, ``transform``, ``encode_snp_matrix``, and a
  static ``train_val_test_split`` helper.
- Serialise / deserialise via joblib.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_selection import VarianceThreshold

logger = logging.getLogger(__name__)


class SNPPreprocessor:
    """
    Full-pipeline preprocessor for SNP + environmental CSV data.

    Attributes
    ----------
    snp_columns : list[str]
        Ordered list of detected SNP column names.
    env_cols_present : list[str]
        Environmental feature columns found in the training dataset.
    feature_names : list[str]
        All input feature names (SNPs then env), in order.
    label_encoders : dict[str, LabelEncoder]
        One LabelEncoder per categorical target column.
    env_mean : np.ndarray
        Mean env-feature values (used when predicting virtual hybrids
        without explicit environment data).
    """

    SNP_PREFIX     = "SNP_"
    MISSING_ALLELE = "NN"
    ENV_COLS       = ["Rainfall_mm", "Temp_C", "Humidity_pct"]

    def __init__(self) -> None:
        self.snp_columns:      list[str] = []
        self.env_cols_present: list[str] = []
        self.feature_names:    list[str] = []
        self.snp_encoders:     dict[str, dict[str, int]] = {}
        self.snp_modes:        dict[str, str] = {}
        self.env_scaler:       StandardScaler = StandardScaler()
        self.label_encoders:   dict[str, LabelEncoder] = {}
        self.env_mean:         np.ndarray | None = None
        self.variance_selector: VarianceThreshold | None = None
        self.top_feature_indices: np.ndarray | None = None

    # ── Column detection ──────────────────────────────────────────────────────

    def _detect_columns(self, df: pd.DataFrame) -> None:
        self.snp_columns = [c for c in df.columns if c.startswith(self.SNP_PREFIX)]
        self.env_cols_present = [c for c in self.ENV_COLS if c in df.columns]
        logger.info(
            "Detected %d SNP columns, %d env columns.",
            len(self.snp_columns), len(self.env_cols_present),
        )

    # ── SNP encoding ──────────────────────────────────────────────────────────

    def _fit_snp_encoder(self, series: pd.Series) -> tuple[dict[str, int], str]:
        """
        Build a deterministic 0/1/2 encoding for one SNP column.

        Strategy
        --------
        * Replace ``NN`` with NaN, compute the mode, fill NaNs.
        * Identify homozygous alleles (same letter twice) and heterozygous.
        * Assign: homo[0] → 0, het → 1, homo[1] → 2.
        """
        clean = series.replace(self.MISSING_ALLELE, None)
        mode_series = clean.mode()
        mode_val: str = mode_series.iloc[0] if not mode_series.empty else "AA"
        clean = clean.fillna(mode_val)

        unique_vals = sorted(clean.dropna().unique())
        homo = sorted([v for v in unique_vals if len(v) == 2 and v[0] == v[1]])
        het  = sorted([v for v in unique_vals if len(v) == 2 and v[0] != v[1]])

        encoding: dict[str, int] = {}
        if len(homo) >= 2:
            encoding[homo[0]] = 0
            for h in het:
                encoding[h] = 1
            encoding[homo[1]] = 2
        elif len(homo) == 1:
            encoding[homo[0]] = 0
            for i, h in enumerate(het, start=1):
                encoding[h] = min(i, 2)
        else:
            for i, v in enumerate(unique_vals):
                encoding[v] = min(i, 2)

        return encoding, mode_val

    def _apply_snp_encoder(
        self,
        series: pd.Series,
        encoding: dict[str, int],
        mode_val: str,
    ) -> np.ndarray:
        """Map a raw SNP series to numeric dosage values."""
        clean = series.replace(self.MISSING_ALLELE, mode_val)
        return clean.map(lambda x: encoding.get(str(x), 0)).astype(np.float32).values

    # ── Public API ────────────────────────────────────────────────────────────

    def fit_transform(
        self, df: pd.DataFrame
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """
        Fit all encoders on ``df`` and return ``(X, y)``.

        ``X`` shape: (n_rows, n_snps + n_env_features).
        ``y`` is a dict: ``{"yield": array, "Disease_Resistance": array, ...}``
        """
        from config import YIELD_TARGET, CATEGORICAL_TARGETS

        self._detect_columns(df)

        # ── SNP encoding ──────────────────────────────────────────────────────
        snp_arrays: list[np.ndarray] = []
        for col in self.snp_columns:
            enc, mode = self._fit_snp_encoder(df[col])
            self.snp_encoders[col] = enc
            self.snp_modes[col] = mode
            snp_arrays.append(self._apply_snp_encoder(df[col], enc, mode))

        X_snp = np.column_stack(snp_arrays) if snp_arrays else np.zeros((len(df), 0))

        # ── Feature Engineering (Biological) ──────────────────────────────────
        if X_snp.shape[1] > 0:
            genomic_heterozygosity = np.sum(X_snp == 1, axis=1, keepdims=True) / X_snp.shape[1]
            total_minor_alleles = np.sum(X_snp, axis=1, keepdims=True)
            X_bio = np.hstack([genomic_heterozygosity, total_minor_alleles]).astype(np.float32)
        else:
            X_bio = np.zeros((len(df), 2), dtype=np.float32)

        # ── Environmental features ────────────────────────────────────────────
        if self.env_cols_present:
            X_env_raw = df[self.env_cols_present].values.astype(np.float32)
            X_env = self.env_scaler.fit_transform(X_env_raw).astype(np.float32)
            self.env_mean = self.env_scaler.mean_.astype(np.float32)
        else:
            X_env = np.zeros((len(df), 0), dtype=np.float32)
            self.env_mean = np.zeros(0, dtype=np.float32)

        X = np.hstack([X_snp, X_bio, X_env]).astype(np.float32)
        
        # ── Variance Threshold ────────────────────────────────────────────────
        self.variance_selector = VarianceThreshold(threshold=0.01) # Remove features with <1% variance
        X = self.variance_selector.fit_transform(X)
        
        bio_names = ["genomic_heterozygosity", "total_minor_alleles"]
        all_features = list(self.snp_columns) + bio_names + list(self.env_cols_present)
        self.feature_names = [all_features[i] for i in range(len(all_features)) if self.variance_selector.get_support()[i]]
        logger.info("Feature matrix shape after fit_transform (and variance filtering): %s", X.shape)

        # ── Targets ───────────────────────────────────────────────────────────
        y: dict[str, np.ndarray] = {}

        if YIELD_TARGET in df.columns:
            y["yield"] = df[YIELD_TARGET].values.astype(np.float32)

        for cat_col in CATEGORICAL_TARGETS:
            if cat_col in df.columns:
                le = LabelEncoder()
                y[cat_col] = le.fit_transform(df[cat_col].astype(str))
                self.label_encoders[cat_col] = le
                logger.info("Label classes for %s: %s", cat_col, le.classes_.tolist())

        return X, y

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform new data using the fitted encoders (no target needed)."""
        snp_arrays: list[np.ndarray] = []
        for col in self.snp_columns:
            enc  = self.snp_encoders[col]
            mode = self.snp_modes[col]
            arr  = self._apply_snp_encoder(df[col], enc, mode) if col in df.columns \
                   else np.zeros(len(df), dtype=np.float32)
            snp_arrays.append(arr)

        X_snp = np.column_stack(snp_arrays) if snp_arrays else np.zeros((len(df), 0))

        if X_snp.shape[1] > 0:
            genomic_heterozygosity = np.sum(X_snp == 1, axis=1, keepdims=True) / X_snp.shape[1]
            total_minor_alleles = np.sum(X_snp, axis=1, keepdims=True)
            X_bio = np.hstack([genomic_heterozygosity, total_minor_alleles]).astype(np.float32)
        else:
            X_bio = np.zeros((len(df), 2), dtype=np.float32)

        if self.env_cols_present:
            avail = [c for c in self.env_cols_present if c in df.columns]
            if avail:
                X_env_raw = df[avail].values.astype(np.float32)
                X_env = self.env_scaler.transform(X_env_raw).astype(np.float32)
            else:
                X_env = np.zeros((len(df), len(self.env_cols_present)), dtype=np.float32)
        else:
            X_env = np.zeros((len(df), 0), dtype=np.float32)

        X = np.hstack([X_snp, X_bio, X_env]).astype(np.float32)
        if self.variance_selector is not None:
            try:
                X = self.variance_selector.transform(X)
            except Exception:
                pass
        
        if self.top_feature_indices is not None:
            X = X[:, self.top_feature_indices]
            
        return X

    def encode_snp_matrix(self, df: pd.DataFrame) -> np.ndarray:
        """
        Return the encoded SNP-only matrix (no env features).

        Shape: (n_rows, n_snps).
        One row per dataset row; genotype is identical across env rows
        for the same line — the caller should deduplicate by line ID first.
        """
        arrays: list[np.ndarray] = []
        for col in self.snp_columns:
            enc  = self.snp_encoders[col]
            mode = self.snp_modes[col]
            arr  = self._apply_snp_encoder(df[col], enc, mode) if col in df.columns \
                   else np.zeros(len(df), dtype=np.float32)
            arrays.append(arr)
        return np.column_stack(arrays).astype(np.float32) if arrays else np.zeros((len(df), 0))

    def normalised_env_vector(self) -> np.ndarray:
        """
        Return the zero-vector in normalised env space (global mean).

        Used as the environmental feature for virtual hybrids when no
        explicit environment is specified.
        """
        # Zero in normalised space = the training mean in original space.
        return np.zeros(len(self.env_cols_present), dtype=np.float32)

    # ── Train / val / test split ──────────────────────────────────────────────

    @staticmethod
    def train_val_test_split(
        X: np.ndarray,
        y: dict[str, np.ndarray],
        train_ratio: float = 0.70,
        val_ratio:   float = 0.15,
        random_state: int  = 42,
    ) -> tuple[
        tuple[np.ndarray, dict],
        tuple[np.ndarray, dict],
        tuple[np.ndarray, dict],
    ]:
        """
        Deterministic shuffle-split into train / val / test.

        Returns three ``(X, y_dict)`` tuples.
        """
        n = len(X)
        rng = np.random.RandomState(random_state)
        idx = rng.permutation(n)

        n_train = int(n * train_ratio)
        n_val   = int(n * val_ratio)

        train_idx = idx[:n_train]
        val_idx   = idx[n_train : n_train + n_val]
        test_idx  = idx[n_train + n_val :]

        def _slice(arr_dict: dict, indices: np.ndarray) -> dict:
            return {k: v[indices] for k, v in arr_dict.items()}

        return (
            (X[train_idx], _slice(y, train_idx)),
            (X[val_idx],   _slice(y, val_idx)),
            (X[test_idx],  _slice(y, test_idx)),
        )

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self, path)
        logger.info("Preprocessor saved → %s", path)

    @classmethod
    def load(cls, path: str) -> "SNPPreprocessor":
        instance = joblib.load(path)
        logger.info("Preprocessor loaded ← %s", path)
        return instance
