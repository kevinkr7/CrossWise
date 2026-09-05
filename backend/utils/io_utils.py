"""
utils/io_utils.py — Filesystem helpers for CrossWire backend.
"""

import os
import glob


def ensure_dir(path: str) -> None:
    """Create directory (and parents) if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def current_dataset_path(upload_dir: str, fallback_path: str) -> str:
    """
    Return the most recently uploaded CSV path, falling back to the
    bundled synthetic dataset if no uploads exist.

    Parameters
    ----------
    upload_dir : str
        Directory where user uploads are saved.
    fallback_path : str
        Absolute path to the bundled dataset CSV.

    Returns
    -------
    str
        Path to the CSV to use for training / recommendation.
    """
    import csv
    ensure_dir(upload_dir)
    uploads = sorted(
        glob.glob(os.path.join(upload_dir, "*.csv")),
        key=os.path.getmtime,
        reverse=True,
    )
    for p in uploads:
        try:
            with open(p, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                if "Yield_t_ha" in headers:
                    return p
        except Exception:
            continue
    return fallback_path


def safe_remove(path: str) -> None:
    """Remove a file without raising if it does not exist."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
