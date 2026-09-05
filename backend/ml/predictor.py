"""
ml/predictor.py — Batch prediction engine for virtual parent pairs.

The core challenge: for 1 000 unique lines, we have 499 500 pairs.
Holding all 499 500 × 300-feature mid-parent vectors in memory at once
would require ~600 MB (float32).  This module solves that with a chunked
approach: it iterates over pair indices in slices of ``PREDICT_BATCH_SIZE``
(default 10 000), predicts each chunk, then collects results.

Confidence is computed only for the top-N pairs (by composite score) via
``predict_proba``, so the expensive proba call scales with ``top_n``,
not with the total pair count.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from config import PREDICT_BATCH_SIZE

if TYPE_CHECKING:
    from ml.models.random_forest_model import RandomForestBreedingModel

logger = logging.getLogger(__name__)


def predict_batch(
    pair_indices: np.ndarray,          # shape (n_pairs, 2): (idx_a, idx_b)
    line_ids:     list[str],
    snp_matrix:   np.ndarray,          # shape (n_unique_lines, n_snps)
    env_vector:   np.ndarray,          # shape (n_env_features,) – normalised mean
    model: "RandomForestBreedingModel",
    preprocessor: Any = None,
    label_encoders: dict[str, Any] | None = None,
    chunk_size:   int = PREDICT_BATCH_SIZE,
) -> list[dict]:
    """
    Run multi-output inference for every parent pair.

    Parameters
    ----------
    pair_indices : ndarray, shape (n_pairs, 2)
        Each row is ``(idx_a, idx_b)`` – indices into ``snp_matrix``.
    line_ids : list[str]
        Parallel list of line identifiers for ``snp_matrix`` rows.
    snp_matrix : ndarray, shape (n_unique_lines, n_snps)
        Encoded SNP dosage matrix for the unique set of parent lines.
    env_vector : ndarray, shape (n_env_features,)
        Normalised environmental feature vector appended to every pair.
        Pass the preprocessor's ``normalised_env_vector()`` (global mean).
    model : RandomForestBreedingModel
        Fitted multi-output RF model.
    chunk_size : int
        Number of pairs to process per iteration.

    Returns
    -------
    list[dict]
        One dict per pair with keys:
        ``idx_a, idx_b, id_a, id_b, predicted_yield, predicted_drought,
        predicted_disease, genomic_compatibility``.
    """
    n_pairs     = len(pair_indices)
    n_env       = len(env_vector)
    n_snps      = snp_matrix.shape[1]
    n_features  = n_snps + n_env

    results: list[dict] = []

    # Pre-tile the env vector if it has values
    env_row = env_vector.reshape(1, -1) if n_env > 0 else np.zeros((1, 0), dtype=np.float32)

    logger.info(
        "Starting batch prediction: %d pairs, chunk_size=%d, feature_dim=%d",
        n_pairs, chunk_size, n_features,
    )

    for start in range(0, n_pairs, chunk_size):
        end   = min(start + chunk_size, n_pairs)
        chunk = pair_indices[start:end]            # (batch, 2)

        idx_a = chunk[:, 0]
        idx_b = chunk[:, 1]

        # Mid-parent SNP feature vectors
        X_snp = (snp_matrix[idx_a] + snp_matrix[idx_b]) / 2.0  # (batch, n_snps)

        # Append biological features (computed from mid-parent SNPs)
        if X_snp.shape[1] > 0:
            genomic_heterozygosity = np.sum(X_snp == 1, axis=1, keepdims=True) / X_snp.shape[1]
            total_minor_alleles = np.sum(X_snp, axis=1, keepdims=True)
            X_bio = np.hstack([genomic_heterozygosity, total_minor_alleles]).astype(np.float32)
        else:
            X_bio = np.zeros((len(chunk), 2), dtype=np.float32)

        # Append env features (broadcast the global mean row)
        if n_env > 0:
            X_env = np.tile(env_row, (len(chunk), 1))            # (batch, n_env)
            X = np.hstack([X_snp, X_bio, X_env]).astype(np.float32)
        else:
            X = np.hstack([X_snp, X_bio]).astype(np.float32)

        # Apply preprocessor variance and feature selection
        if hasattr(preprocessor, "variance_selector") and preprocessor.variance_selector is not None:
            try:
                X = preprocessor.variance_selector.transform(X)
            except Exception:
                pass
        
        if hasattr(preprocessor, "top_feature_indices") and preprocessor.top_feature_indices is not None:
            X = X[:, preprocessor.top_feature_indices]

        preds = model.predict(X)

        # Genomic compatibility: 1 – mean(|dosage_A – dosage_B|) / 2
        compat = 1.0 - np.mean(
            np.abs(snp_matrix[idx_a] - snp_matrix[idx_b]), axis=1
        ) / 2.0

        for k in range(len(chunk)):
            ia, ib = int(idx_a[k]), int(idx_b[k])
            results.append({
                "idx_a":                 ia,
                "idx_b":                 ib,
                "id_a":                  line_ids[ia],
                "id_b":                  line_ids[ib],
                "predicted_yield":       float(preds.get("yield", [5.0])[k]),
                "predicted_drought":     _decode_label(model, "Drought_Tolerance",  preds, k, label_encoders),
                "predicted_disease":     _decode_label(model, "Disease_Resistance", preds, k, label_encoders),
                "predicted_quality":     _decode_label(model, "Grain_Quality",      preds, k, label_encoders),
                "predicted_maturity":    _decode_label(model, "Maturity_Period",    preds, k, label_encoders),
                "genomic_compatibility": float(np.clip(compat[k], 0.0, 1.0)),
            })

        if start % (chunk_size * 10) == 0:
            logger.info("  … processed %d / %d pairs", end, n_pairs)

    logger.info("Batch prediction complete. %d results.", len(results))
    return results


def compute_confidence_for_top(
    top_results: list[dict],
    snp_matrix:  np.ndarray,
    env_vector:  np.ndarray,
    model:       "RandomForestBreedingModel",
    preprocessor: Any = None,
) -> list[dict]:
    """
    Enrich the top-N results with classifier confidence scores.

    Confidence = max probability across disease × drought classes,
    then averaged.
    """
    if not top_results:
        return top_results

    n_env  = len(env_vector)
    idx_a  = np.array([r["idx_a"] for r in top_results])
    idx_b  = np.array([r["idx_b"] for r in top_results])

    X_snp = (snp_matrix[idx_a] + snp_matrix[idx_b]) / 2.0
    if X_snp.shape[1] > 0:
        genomic_heterozygosity = np.sum(X_snp == 1, axis=1, keepdims=True) / X_snp.shape[1]
        total_minor_alleles = np.sum(X_snp, axis=1, keepdims=True)
        X_bio = np.hstack([genomic_heterozygosity, total_minor_alleles]).astype(np.float32)
    else:
        X_bio = np.zeros((len(top_results), 2), dtype=np.float32)

    if n_env > 0:
        X_env = np.tile(env_vector.reshape(1, -1), (len(top_results), 1))
        X = np.hstack([X_snp, X_bio, X_env]).astype(np.float32)
    else:
        X = np.hstack([X_snp, X_bio]).astype(np.float32)

    if hasattr(preprocessor, "variance_selector") and preprocessor.variance_selector is not None:
        try:
            X = preprocessor.variance_selector.transform(X)
        except Exception:
            pass
            
    if hasattr(preprocessor, "top_feature_indices") and preprocessor.top_feature_indices is not None:
        X = X[:, preprocessor.top_feature_indices]

    probas = model.predict_proba(X)

    from config import CATEGORICAL_TARGETS

    for k, res in enumerate(top_results):
        conf_scores = []
        for target in CATEGORICAL_TARGETS:
            if target in probas:
                conf_scores.append(float(probas[target][k].max()))
        if conf_scores:
            res["confidence"] = float(np.mean(conf_scores))

    return top_results


# ── Internal helpers ─────────────────────────────────────────────────────────

def _decode_label(
    model: "RandomForestBreedingModel",
    target_name: str,
    preds: dict,
    k: int,
    label_encoders: dict[str, Any] | None = None,
) -> str:
    """Convert numeric classifier output back to its original string class using LabelEncoders."""
    if target_name not in preds:
        return "Unknown"

    raw_label = preds[target_name][k]   # int (label-encoded index)

    if label_encoders and target_name in label_encoders:
        try:
            return str(label_encoders[target_name].inverse_transform([int(raw_label)])[0])
        except Exception:
            pass

    return str(raw_label)
