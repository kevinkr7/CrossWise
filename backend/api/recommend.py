"""
api/recommend.py — Blueprint for /recommend route (legacy).

This blueprint is kept for backward compat. The primary recommendation
endpoint is now ``POST /api/recommend/snp`` in ``routes/api.py``.
"""

from flask import Blueprint, jsonify

recommend_bp = Blueprint("recommend", __name__)


@recommend_bp.route("/recommend", methods=["POST"])
def recommend():
    """Redirect to the canonical recommendation endpoint docs."""
    return jsonify({
        "info": "This legacy endpoint is deprecated.",
        "use":  "POST /api/recommend/snp  (full SNP pipeline)",
        "docs": "GET  /api/model/status  (check training status)",
    }), 308
