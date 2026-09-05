"""
routes/api.py — REST API endpoints for CrossWire SNP Breeding Framework.

Endpoints
---------
GET  /api/health            — Server + model health check
GET  /api/model/status      — Trained model metrics + training timestamp
GET  /api/dataset/info      — Dataset summary statistics
POST /api/upload            — Upload SNP / env / phenotypic CSV files
POST /api/train             — Trigger model re-training
POST /api/recommend/snp     — Full SNP-based recommendation pipeline
GET  /api/shap              — SHAP feature importance (live or cached)
POST /api/predict/manual    — (Legacy) Nucleotide fraction prediction
POST /api/predict/fasta     — (Legacy) FASTA-based prediction
"""

from __future__ import annotations

import io
import logging
import os
import time
import uuid

import numpy as np
import pandas as pd
from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_artefacts():
    return current_app.config.get("ARTEFACTS")


def _reload_artefacts():
    """Re-load artefacts from disk after training and update app.config."""
    try:
        from ml.trainer import load_trained_artefacts
        arts = load_trained_artefacts()
        current_app.config["ARTEFACTS"] = arts
        return arts
    except Exception as exc:
        logger.error("Failed to reload artefacts: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/health", methods=["GET"])
@api_bp.route("/api/health", methods=["GET"])
def health():
    arts = _get_artefacts()
    return jsonify({
        "status":       "healthy",
        "model_loaded": arts is not None,
        "version":      "2.0",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Model status
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/api/model/status", methods=["GET"])
def model_status():
    from config import RF_MODEL_PATH, PREPROCESSOR_PATH, SESSION_DATA_PATH
    arts = _get_artefacts()

    trained = arts is not None
    metrics = {}
    n_snp_features = 0
    n_features = 0
    dataset_rows = 0

    if trained:
        session = arts.get("session", {})
        metrics      = session.get("metrics", {})
        n_features   = metrics.get("n_features", 0)
        n_snp_features = metrics.get("n_snp_features", 0)
        dataset_rows = metrics.get("dataset_rows", 0)

    # File timestamps
    mtime = None
    if os.path.exists(RF_MODEL_PATH):
        mtime = time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.localtime(os.path.getmtime(RF_MODEL_PATH)),
        )

    return jsonify({
        "trained":         trained,
        "trained_at":      mtime,
        "metrics":         metrics,
        "n_features":      n_features,
        "n_snp_features":  n_snp_features,
        "dataset_rows":    dataset_rows,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Dataset info
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/api/dataset/info", methods=["GET"])
def dataset_info():
    arts = _get_artefacts()
    if not arts:
        return jsonify({"error": "Model not trained yet."}), 503

    session = arts.get("session", {})
    metrics = session.get("metrics", {})

    line_ids   = session.get("line_ids", [])
    n_unique   = len(set(line_ids))
    n_pairs    = n_unique * (n_unique - 1) // 2
    preprocessor = arts.get("preprocessor")
    n_snps     = len(preprocessor.snp_columns) if preprocessor else 0

    # Yield stats from the session
    y_test = session.get("y_test", {})
    if isinstance(y_test, dict) and "yield" in y_test:
        y_arr = y_test["yield"]
        yield_mean = round(float(np.mean(y_arr)), 2)
        yield_std  = round(float(np.std(y_arr)),  2)
    else:
        yield_mean = yield_std = None

    return jsonify({
        "total_rows":     metrics.get("dataset_rows", 0),
        "unique_lines":   n_unique,
        "n_snp_markers":  n_snps,
        "n_environments": 6,
        "n_pairs_possible": n_pairs,
        "yield_mean":     yield_mean,
        "yield_std":      yield_std,
        "missing_rate":   "~2%",
        "dataset_path":   os.path.basename(session.get("dataset_path", "")),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/api/upload", methods=["POST"])
def upload_csv():
    """
    Accept multipart CSV upload.

    Fields (at least one required):
      snp_file   — SNP genotype CSV
      env_file   — Environmental CSV (optional if SNP CSV contains env cols)
      pheno_file — Historical phenotypic CSV (optional)

    The server merges the files (joining on Line/Parent_ID) and saves
    the combined dataset to the upload directory.
    """
    from config import UPLOAD_DIR, LINE_ID_COL, SNP_PREFIX, ENV_FEATURES
    from utils.io_utils import ensure_dir

    ensure_dir(UPLOAD_DIR)

    snp_file   = request.files.get("snp_file")
    env_file   = request.files.get("env_file")
    pheno_file = request.files.get("pheno_file")

    if snp_file is None:
        return jsonify({"error": "snp_file is required."}), 400

    try:
        snp_df = pd.read_csv(io.StringIO(snp_file.read().decode("utf-8")))
    except Exception as exc:
        return jsonify({"error": f"Could not parse SNP CSV: {exc}"}), 400

    # Detect line ID column
    line_col = _detect_line_id_col(snp_df)
    if line_col is None:
        return jsonify({
            "error": "SNP CSV must have a column named 'Line', 'Parent_ID', or similar."
        }), 400

    if line_col != LINE_ID_COL:
        snp_df = snp_df.rename(columns={line_col: LINE_ID_COL})

    snp_cols = [c for c in snp_df.columns if c.startswith(SNP_PREFIX)]
    if len(snp_cols) < 10:
        return jsonify({
            "error": f"SNP CSV must contain at least 10 columns with prefix '{SNP_PREFIX}'. Found {len(snp_cols)}."
        }), 400

    # Merge environmental CSV
    combined = snp_df.copy()
    if env_file:
        try:
            env_df = pd.read_csv(io.StringIO(env_file.read().decode("utf-8")))
            env_df = _normalise_env_columns(env_df)
            # If env CSV has no line ID, broadcast a single row to all lines
            if LINE_ID_COL in env_df.columns:
                combined = combined.merge(env_df, on=LINE_ID_COL, how="left")
            else:
                for col in env_df.columns:
                    combined[col] = env_df[col].iloc[0]
        except Exception as exc:
            logger.warning("Could not merge env CSV: %s", exc)

    # Merge phenotypic CSV (optional)
    if pheno_file:
        try:
            pheno_df = pd.read_csv(io.StringIO(pheno_file.read().decode("utf-8")))
            pheno_df = _normalise_pheno_columns(pheno_df)
            if LINE_ID_COL in pheno_df.columns:
                combined = combined.merge(pheno_df, on=LINE_ID_COL, how="left")
        except Exception as exc:
            logger.warning("Could not merge phenotypic CSV: %s", exc)

    # Save combined dataset
    filename = f"upload_{uuid.uuid4().hex[:8]}.csv"
    save_path = os.path.join(UPLOAD_DIR, filename)
    combined.to_csv(save_path, index=False)

    env_cols_found = [c for c in ENV_FEATURES if c in combined.columns]
    has_traits = any(c in combined.columns for c in ["Yield_t_ha", "Disease_Resistance", "Drought_Tolerance", "Grain_Quality", "Maturity_Period"])

    return jsonify({
        "status":        "success",
        "filename":      filename,
        "rows":          len(combined),
        "snp_markers":   len(snp_cols),
        "env_features":  env_cols_found,
        "has_traits":    has_traits,
        "unique_lines":  int(combined[LINE_ID_COL].nunique()),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Train
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/api/train", methods=["POST"])
def train():
    """Trigger model training. Returns training metrics on success."""
    body       = request.get_json(silent=True) or {}
    model_name = body.get("model_name", "random_forest")

    try:
        from ml.trainer import train_model
        metrics = train_model(model_name=model_name)
    except Exception as exc:
        logger.error("Training failed: %s", exc, exc_info=True)
        return jsonify({"error": f"Training failed: {exc}"}), 500

    # Reload artefacts
    _reload_artefacts()

    return jsonify({"status": "success", "metrics": metrics})


# ─────────────────────────────────────────────────────────────────────────────
# SNP Recommendation Pipeline
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/api/recommend/snp", methods=["POST"])
def recommend_snp():
    """
    Full SNP-based recommendation pipeline.

    Body (JSON, all optional):
      top_n            : int   (default 5)
      location_filter  : str   (e.g. "Coimbatore")
    """
    arts = _get_artefacts()
    if not arts:
        return jsonify({"error": "Model not trained. Visit /upload to train."}), 503

    model        = arts["model"]
    session_data = arts["session"]
    preprocessor = arts["preprocessor"]

    body       = request.get_json(silent=True) or {}
    top_n      = int(body.get("top_n", 5))
    loc_filter = body.get("location_filter") or body.get("location")
    candidate_file = body.get("candidate_file")

    if candidate_file:
        from config import UPLOAD_DIR, LINE_ID_COL
        import pandas as pd
        
        filepath = os.path.join(UPLOAD_DIR, candidate_file)
        if not os.path.exists(filepath):
            return jsonify({"error": "Candidate file not found. Please upload again."}), 404
        
        try:
            df = pd.read_csv(filepath)
            
            # Deduplicate by LINE_ID_COL to get unique parent candidates
            # (If env data was merged, there might be duplicate lines. We only need the genotype once per line for generating crosses)
            if LINE_ID_COL in df.columns:
                df_unique = df.drop_duplicates(subset=[LINE_ID_COL])
                line_ids = df_unique[LINE_ID_COL].astype(str).tolist()
            else:
                df_unique = df
                line_ids = [f"Candidate_{i}" for i in range(len(df_unique))]
                
            snp_matrix = preprocessor.encode_snp_matrix(df_unique)
            
        except Exception as exc:
            return jsonify({"error": f"Failed to process candidate file: {exc}"}), 400
    else:
        line_ids   = session_data["line_ids"]
        snp_matrix = session_data["snp_matrix"]   # (n_rows, n_snps) — has env rows

    # Generate pairs
    from core.parent_generator import generate_all_pairs
    pair_indices, unique_ids, snp_unique, compat_vec = generate_all_pairs(
        encoded_snp_matrix=snp_matrix,
        line_ids=line_ids,
    )
    total_pairs = len(pair_indices)

    # Apply Environmental Location Filter to prediction
    env_vec = preprocessor.normalised_env_vector()
    if loc_filter:
        try:
            # We have 6 environments in the synthetic dataset with mean values
            LOCATION_ENV_MEANS = {
                "coimbatore": [650.0, 29.5, 68.0],
                "mandya": [780.0, 27.0, 72.0],
                "davangere": [430.0, 25.5, 58.0],
                "anantapur": [390.0, 31.0, 52.0],
                "warangal": [410.0, 26.5, 60.0],
                "bengaluru rural": [720.0, 26.0, 70.0],
            }
            if loc_filter.lower() in LOCATION_ENV_MEANS:
                import numpy as np
                raw_means = LOCATION_ENV_MEANS[loc_filter.lower()]
                # Order in ENV_COLS is ["Rainfall_mm", "Temp_C", "Humidity_pct"]
                # preprocessor.env_scaler expects this order.
                env_vec_raw = np.array([raw_means], dtype=np.float32)
                env_vec = preprocessor.env_scaler.transform(env_vec_raw)[0].astype(np.float32)
        except Exception as exc:
            logger.warning("Location env vector transform failed: %s. Proceeding with global mean.", exc)

    # Batch predict
    from ml.predictor import predict_batch
    results = predict_batch(
        pair_indices=pair_indices,
        line_ids=unique_ids,
        snp_matrix=snp_unique,
        env_vector=env_vec,
        model=model,
        preprocessor=preprocessor,
        label_encoders=preprocessor.label_encoders,
    )

    # Rank using vectorised engine
    from core.recommendation_engine import RecommendationEngine
    engine = RecommendationEngine(top_n=top_n)

    predicted_yield    = np.array([r["predicted_yield"]      for r in results], dtype=np.float32)
    predicted_drought  = np.array([r["predicted_drought"]    for r in results])
    predicted_disease  = np.array([r["predicted_disease"]    for r in results])
    predicted_quality  = np.array([r["predicted_quality"]    for r in results])
    predicted_maturity = np.array([r["predicted_maturity"]   for r in results])
    compat             = np.array([r["genomic_compatibility"] for r in results], dtype=np.float32)

    scores = engine.rank_vectorised(predicted_yield, predicted_drought, predicted_disease, predicted_quality, predicted_maturity, compat)

    # Get top-N indices
    top_indices = np.argsort(scores)[::-1][:top_n]
    top_results = [results[i] for i in top_indices]
    for i, r in enumerate(top_results):
        r["recommendation_score"] = float(scores[top_indices[i]])

    # Compute confidence only for top-N
    from ml.predictor import compute_confidence_for_top
    top_results = compute_confidence_for_top(top_results, snp_unique, env_vec, model, preprocessor)

    # Format response
    recommendations = engine.build_recommendation_response(top_results)

    # Cache for SHAP endpoint
    current_app.config["LAST_RECOMMENDATION"] = {
        "top_pairs":  top_results,
        "snp_matrix": snp_unique,
        "line_ids":   unique_ids,
    }

    return jsonify({
        "status":               "success",
        "total_pairs_evaluated": total_pairs,
        "unique_parents":       len(unique_ids),
        "location_filter":      loc_filter or "All Environments",
        "top_recommendations":  recommendations,
    })


# ─────────────────────────────────────────────────────────────────────────────
# SHAP Explainability
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/api/shap", methods=["GET"])
def shap_analysis():
    """
    Compute SHAP feature importance for the yield regressor.

    Uses SHAP TreeExplainer on up to 200 test-set samples.
    Falls back to RF feature_importances_ if shap is not installed.
    """
    from config import SHAP_MAX_SAMPLES, SHAP_TOP_K_FEATURES

    # Return cached SHAP analysis immediately if available
    cached = current_app.config.get("SHAP_CACHE")
    if cached:
        return jsonify(cached)

    arts = _get_artefacts()
    if not arts:
        return jsonify({"error": "Model not trained."}), 503

    model        = arts["model"]
    preprocessor = arts["preprocessor"]
    session_data = arts["session"]

    X_test = session_data.get("X_test")
    if X_test is None or len(X_test) == 0:
        return jsonify({"error": "No test data available for SHAP analysis."}), 503

    feature_names = preprocessor.feature_names
    regressor = model.regressor

    if regressor is None:
        return jsonify({"error": "Yield regressor not available."}), 503

    # Subsample
    n_samples = min(SHAP_MAX_SAMPLES, len(X_test))
    idx       = np.random.choice(len(X_test), n_samples, replace=False)
    X_sub     = X_test[idx]

    try:
        import shap
        bg_size    = min(50, len(X_sub))
        background = shap.maskers.Independent(X_sub[:bg_size], max_samples=bg_size)
        explainer  = shap.TreeExplainer(regressor, background)
        shap_vals  = explainer.shap_values(X_sub)

        mean_abs_shap = np.abs(shap_vals).mean(axis=0)
        top_k_idx     = np.argsort(mean_abs_shap)[::-1][:SHAP_TOP_K_FEATURES]

        features = []
        for rank, fi in enumerate(top_k_idx):
            fname = feature_names[fi] if fi < len(feature_names) else f"Feature_{fi}"
            features.append({
                "rank":      rank + 1,
                "name":      fname,
                "mean_shap": round(float(mean_abs_shap[fi]), 4),
                "shap_vals": shap_vals[:, fi].tolist()[:50],  # first 50 samples
                "feat_vals": X_sub[:, fi].tolist()[:50],
            })

        result = {"method": "shap_tree_explainer", "features": features}
        current_app.config["SHAP_CACHE"] = result
        return jsonify(result)

    except ImportError:
        # Graceful fallback: use built-in RF feature_importances_
        logger.warning("shap not installed — falling back to RF feature_importances_.")
        importances = regressor.feature_importances_
        top_k_idx   = np.argsort(importances)[::-1][:SHAP_TOP_K_FEATURES]

        features = []
        for rank, fi in enumerate(top_k_idx):
            fname = feature_names[fi] if fi < len(feature_names) else f"Feature_{fi}"
            features.append({
                "rank":      rank + 1,
                "name":      fname,
                "mean_shap": round(float(importances[fi]), 4),
            })

        result = {"method": "rf_feature_importance", "features": features}
        current_app.config["SHAP_CACHE"] = result
        return jsonify(result)

    except Exception as exc:
        logger.error("SHAP analysis failed: %s", exc, exc_info=True)
        return jsonify({"error": f"SHAP analysis failed: {exc}"}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_line_id_col(df: pd.DataFrame) -> str | None:
    """Find the line/parent ID column by checking common names."""
    candidates = ["Line", "line", "Parent_ID", "parent_id", "ParentID",
                  "ID", "id", "Name", "Genotype"]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _normalise_env_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename environmental CSV columns to the standard names."""
    from config import ENV_CSV_ALIASES
    rename = {}
    for col in df.columns:
        key = col.lower().replace(" ", "_")
        if key in ENV_CSV_ALIASES:
            rename[col] = ENV_CSV_ALIASES[key]
    return df.rename(columns=rename)


def _normalise_pheno_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename phenotypic CSV columns to the standard names."""
    from config import PHENO_CSV_ALIASES
    rename = {}
    for col in df.columns:
        key = col.lower().replace(" ", "_")
        if key in PHENO_CSV_ALIASES:
            rename[col] = PHENO_CSV_ALIASES[key]
    return df.rename(columns=rename)


# ─────────────────────────────────────────────────────────────────────────────
# History
# ─────────────────────────────────────────────────────────────────────────────

from flask_jwt_extended import jwt_required, get_jwt_identity

@api_bp.route("/api/history", methods=["GET"])
@jwt_required()
def get_history():
    from models.history import History
    user_id = get_jwt_identity()
    try:
        results = History.get_user_history(user_id)
        return jsonify({"status": "success", "history": results})
    except Exception as exc:
        logger.error("Failed to get history: %s", exc)
        return jsonify({"error": str(exc)}), 500

@api_bp.route("/api/history", methods=["POST"])
@jwt_required()
def save_history():
    from models.history import History
    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}
    try:
        saved = History.save_run(user_id, body)
        return jsonify({"status": "success", "id": saved["_id"]}), 201
    except Exception as exc:
        logger.error("Failed to save history: %s", exc)
        return jsonify({"error": str(exc)}), 500

@api_bp.route("/api/history", methods=["DELETE"])
@jwt_required()
def clear_history():
    from models.history import History
    user_id = get_jwt_identity()
    try:
        count = History.clear_user_history(user_id)
        return jsonify({"status": "success", "deleted_count": count})
    except Exception as exc:
        logger.error("Failed to clear history: %s", exc)
        return jsonify({"error": str(exc)}), 500
