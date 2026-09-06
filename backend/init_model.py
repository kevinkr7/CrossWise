"""
backend/init_model.py — Build-time model training script.
Ensures machine learning artefacts exist BEFORE Gunicorn starts,
so the server binds to the port instantly and avoids Render port scan timeouts.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import RF_MODEL_PATH, PREPROCESSOR_PATH
from ml.trainer import train_model

if not (os.path.exists(RF_MODEL_PATH) and os.path.exists(PREPROCESSOR_PATH)):
    print("[INIT_MODEL] Training lightweight Random Forest models for deployment...")
    metrics = train_model()
    print("[INIT_MODEL] Training complete! Metrics:", metrics)
else:
    print("[INIT_MODEL] Model artefacts already exist, skipping build-time train.")
