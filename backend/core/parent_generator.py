"""
core/parent_generator.py — Generate all unique virtual parent combinations.

Given n unique inbred lines, this module produces all n(n-1)/2 ordered pairs
along with their mid-parent SNP feature vectors and genomic compatibility scores.

Genomic compatibility
---------------------
Defined here as 1 − mean(|dosage_A − dosage_B|) / 2, which lies in [0, 1].
A value of 1.0 means the two parents are genetically identical (no diversity),
while 0.0 means they differ at every locus.  The sweet-spot for hybrid
breeding is an intermediate value — enough genetic diversity to capture
heterosis while retaining complementary allele combinations.
"""

from __future__ import annotations

import itertools
import logging

import numpy as np

logger = logging.getLogger(__name__)


def generate_pair_indices(n_lines: int) -> np.ndarray:
    """
    Return an (n_pairs, 2) integer array of all unique pair indices.

    Uses ``itertools.combinations`` for memory-efficient iteration, then
    converts to a numpy array in one shot.

    Parameters
    ----------
    n_lines : int
        Number of unique parent lines.

    Returns
    -------
    np.ndarray, shape (n_pairs, 2), dtype int32
    """
    n_pairs = n_lines * (n_lines - 1) // 2
    logger.info("Generating %d unique parent pairs for %d lines.", n_pairs, n_lines)
    pairs = np.fromiter(
        itertools.chain.from_iterable(itertools.combinations(range(n_lines), 2)),
        dtype=np.int32,
        count=n_pairs * 2,
    ).reshape(-1, 2)
    return pairs


def generate_all_pairs(
    encoded_snp_matrix: np.ndarray,
    line_ids:           list[str],
    lines_df=None,         # unused, kept for signature compatibility
) -> tuple[np.ndarray, list[str], np.ndarray]:
    """
    Build the full pair-index array, deduplicated line IDs, and
    a pre-computed compatibility vector.

    Returns
    -------
    pair_indices : ndarray, shape (n_pairs, 2)
    unique_ids   : list[str], length n_unique
    compat_vec   : ndarray, shape (n_pairs,), dtype float32
        Genomic compatibility for every pair (pre-computed here
        so the recommendation engine doesn't have to redo it).
    """
    # Deduplication: keep first occurrence of each line ID
    seen: set[str] = set()
    unique_idx: list[int] = []
    unique_ids: list[str] = []

    for k, lid in enumerate(line_ids):
        if lid not in seen:
            seen.add(lid)
            unique_ids.append(lid)
            unique_idx.append(k)

    snp_unique = encoded_snp_matrix[unique_idx]   # (n_unique, n_snps)
    n_unique   = len(unique_ids)

    pair_indices = generate_pair_indices(n_unique)

    # Pre-compute compatibility scores in vectorised chunks
    logger.info("Pre-computing genomic compatibility for %d pairs …", len(pair_indices))
    compat_vec = _vectorised_compatibility(snp_unique, pair_indices)

    logger.info(
        "Pair generation complete: %d unique lines → %d pairs.",
        n_unique, len(pair_indices),
    )
    return pair_indices, unique_ids, snp_unique, compat_vec


def _vectorised_compatibility(
    snp_matrix:   np.ndarray,
    pair_indices: np.ndarray,
    chunk_size:   int = 10_000,
) -> np.ndarray:
    """
    Compute genomic compatibility for all pairs in vectorised chunks.

    compat_ij = 1 − mean(|dosage_i − dosage_j|) / 2

    Returns
    -------
    ndarray, shape (n_pairs,), dtype float32
    """
    n_pairs  = len(pair_indices)
    compat   = np.empty(n_pairs, dtype=np.float32)

    for start in range(0, n_pairs, chunk_size):
        end       = min(start + chunk_size, n_pairs)
        chunk_idx = pair_indices[start:end]
        diff      = np.abs(
            snp_matrix[chunk_idx[:, 0]] - snp_matrix[chunk_idx[:, 1]]
        )                                   # (batch, n_snps)
        compat[start:end] = 1.0 - diff.mean(axis=1) / 2.0

    return np.clip(compat, 0.0, 1.0)
