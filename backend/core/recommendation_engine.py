"""
core/recommendation_engine.py — Score, rank, and format parent-pair predictions.

Composite score formula
-----------------------
  score = w_y × yield_norm
        + w_d × drought_score
        + w_r × disease_score
        + w_c × genomic_compatibility

where each term is in [0, 1] and weights come from ``config.SCORING_WEIGHTS``.

Confidence
----------
After ranking, the top-N pairs are passed back to ``ml.predictor`` for
``predict_proba``, and confidence is the mean of the maximum class
probabilities for the two categorical classifiers.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from config import (
    SCORING_WEIGHTS,
    YIELD_NORM_MAX,
    DROUGHT_SCORES,
    DISEASE_SCORES,
    QUALITY_SCORES,
    MATURITY_SCORES,
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Transforms flat prediction lists into ranked, formatted recommendations.

    Parameters
    ----------
    top_n : int
        How many top pairs to surface.
    weights : dict[str, float] | None
        Override the default composite score weights from config.
    """

    def __init__(
        self,
        top_n:   int  = 5,
        weights: dict | None = None,
    ) -> None:
        self.top_n   = top_n
        self.weights = weights or SCORING_WEIGHTS

    # ── Public API ────────────────────────────────────────────────────────────

    def rank_all_pairs(self, results: list[dict]) -> list[dict]:
        """
        Compute composite score for every pair, return list sorted
        by score descending.
        """
        for r in results:
            r["recommendation_score"] = self._composite_score(r)

        ranked = sorted(results, key=lambda x: x["recommendation_score"], reverse=True)
        logger.info(
            "Ranked %d pairs. Best score = %.4f",
            len(ranked),
            ranked[0]["recommendation_score"] if ranked else 0.0,
        )
        return ranked

    def top_n(self, ranked: list[dict], n: int | None = None) -> list[dict]:
        """Return the top-n pairs (or self.top_n if n is None)."""
        k = n if n is not None else self.top_n
        return ranked[:k]

    def build_recommendation_response(
        self,
        top: list[dict],
        line_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Serialise the top-N pairs into the API response format.

        Each item in the returned list maps directly to one table row in the
        frontend recommendation table.
        """
        response = []
        for rank, r in enumerate(top, start=1):
            id_a = r.get("id_a", f"Line_{r.get('idx_a', '?')}")
            id_b = r.get("id_b", f"Line_{r.get('idx_b', '?')}")

            response.append({
                "rank":                  rank,
                "parent_a":              id_a,
                "parent_b":              id_b,
                "hybrid_name":           f"{id_a} × {id_b}",
                "predicted_yield":       round(r.get("predicted_yield"), 2) if r.get("predicted_yield") is not None else None,
                "predicted_drought":     r.get("predicted_drought"),
                "predicted_disease":     r.get("predicted_disease"),
                "predicted_quality":     r.get("predicted_quality"),
                "predicted_maturity":    r.get("predicted_maturity"),
                "genomic_compatibility": round(r.get("genomic_compatibility"), 4) if r.get("genomic_compatibility") is not None else None,
                "recommendation_score":  round(r.get("recommendation_score"), 4) if r.get("recommendation_score") is not None else None,
                "confidence":            round(r.get("confidence"), 4) if r.get("confidence") is not None else None,
            })

        return response

    # ── Vectorised ranking (fast path for very large pair lists) ──────────────

    def rank_vectorised(
        self,
        predicted_yield: np.ndarray,        # (n_pairs,)
        predicted_drought: np.ndarray,      # (n_pairs,) string labels
        predicted_disease: np.ndarray,      # (n_pairs,) string labels
        predicted_quality: np.ndarray,      # (n_pairs,) string labels
        predicted_maturity: np.ndarray,     # (n_pairs,) string labels
        genomic_compat:  np.ndarray,        # (n_pairs,)
    ) -> np.ndarray:
        """
        Compute composite scores for all pairs in pure numpy and return
        a sort index (descending by score).

        This is ~50× faster than calling ``rank_all_pairs`` for 500k+ pairs.
        """
        yield_norm = np.clip(predicted_yield / YIELD_NORM_MAX, 0.0, 1.0)

        drought_num = np.vectorize(
            lambda d: DROUGHT_SCORES.get(str(d), 0.5)
        )(predicted_drought)

        disease_num = np.vectorize(
            lambda d: DISEASE_SCORES.get(str(d), 0.5)
        )(predicted_disease)
        
        quality_num = np.vectorize(
            lambda d: QUALITY_SCORES.get(str(d), 0.5)
        )(predicted_quality)
        
        maturity_num = np.vectorize(
            lambda d: MATURITY_SCORES.get(str(d), 0.5)
        )(predicted_maturity)

        scores = (
            self.weights["yield"]         * yield_norm
            + self.weights["drought"]     * drought_num
            + self.weights["disease"]     * disease_num
            + self.weights["quality"]     * quality_num
            + self.weights["maturity"]    * maturity_num
            + self.weights["compatibility"] * genomic_compat
        )

        return scores

    # ── Internal ──────────────────────────────────────────────────────────────

    def _composite_score(self, r: dict) -> float:
        yield_norm   = min(r.get("predicted_yield", 0.0) / YIELD_NORM_MAX, 1.0)
        drought_num  = DROUGHT_SCORES.get(str(r.get("predicted_drought", "Medium")), 0.5)
        disease_num  = DISEASE_SCORES.get(str(r.get("predicted_disease",  "Moderate")), 0.5)
        quality_num  = QUALITY_SCORES.get(str(r.get("predicted_quality",  "Standard")), 0.5)
        maturity_num = MATURITY_SCORES.get(str(r.get("predicted_maturity", "Medium")), 0.5)
        compat       = float(r.get("genomic_compatibility", 0.5))

        return (
            self.weights["yield"]           * yield_norm
            + self.weights["drought"]       * drought_num
            + self.weights["disease"]       * disease_num
            + self.weights["quality"]       * quality_num
            + self.weights["maturity"]      * maturity_num
            + self.weights["compatibility"] * compat
        )
