"""
backend/app.py — CrossWire Flask Application Entry Point.

On startup:
  1. Auto-trains the RF model on the bundled dataset if no artefacts exist.
  2. Loads artefacts (model + preprocessor + session data) into app.config.
  3. Registers all blueprints.
"""

import logging
import os

from flask import Flask, render_template, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App factory ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static",
)

CORS(app)

# ── JWT Auth ──────────────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = config.JWT_SECRET_KEY
jwt = JWTManager(app)

# ── Auto-train on startup ─────────────────────────────────────────────────────

def _bootstrap():
    """
    Train the RF model on the bundled synthetic dataset if no persisted
    artefacts are found, then load everything into ``app.config``.
    """
    from config import RF_MODEL_PATH, PREPROCESSOR_PATH, MODELS_DIR
    from utils.io_utils import ensure_dir

    ensure_dir(MODELS_DIR)

    if not (os.path.exists(RF_MODEL_PATH) and os.path.exists(PREPROCESSOR_PATH)):
        logger.info("[BOOTSTRAP] No trained model found — running auto-train on bundled dataset …")
        try:
            from ml.trainer import train_model
            metrics = train_model()
            logger.info("[BOOTSTRAP] Auto-train complete: %s", metrics)
        except Exception as exc:
            logger.error("[BOOTSTRAP] Auto-train failed: %s", exc, exc_info=True)

    # Load artefacts into app context
    try:
        from ml.trainer import load_trained_artefacts
        artefacts = load_trained_artefacts()
        app.config["ARTEFACTS"] = artefacts
        if artefacts:
            logger.info("[BOOTSTRAP] Artefacts loaded successfully.")
        else:
            logger.warning("[BOOTSTRAP] Artefacts could not be loaded (model not yet trained?).")
    except Exception as exc:
        logger.error("[BOOTSTRAP] Could not load artefacts: %s", exc, exc_info=True)
        app.config["ARTEFACTS"] = None


# ── Register blueprints ───────────────────────────────────────────────────────
from routes.views import views_bp
from routes.api import api_bp
from api.recommend import recommend_bp
from routes.auth import auth_bp

app.register_blueprint(views_bp)
app.register_blueprint(api_bp)
app.register_blueprint(recommend_bp)
app.register_blueprint(auth_bp)

# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error"}), 500

# ── Run bootstrap once app context is ready ───────────────────────────────────
with app.app_context():
    _bootstrap()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)