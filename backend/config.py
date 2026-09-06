"""
config.py — Central configuration for CrossWire SNP Breeding Framework.

All paths, constants, and hyperparameters live here so every module
can import from a single source of truth.
"""


import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── Root Paths ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# ── Data Paths ────────────────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Bundled synthetic dataset (fallback when no custom upload)
MAIZE_DATASET_PATH = os.path.join(
    PROJECT_ROOT, "Maize_datasets", "synthetic_maize_dataset.csv"
)
if not os.path.exists(MAIZE_DATASET_PATH):
    # Fallback if working directory is backend/ or root
    alt_path = os.path.join(BASE_DIR, "Maize_datasets", "synthetic_maize_dataset.csv")
    if os.path.exists(alt_path):
        MAIZE_DATASET_PATH = alt_path


# ── Model Artefact Paths ──────────────────────────────────────────────────────
RF_MODEL_PATH      = os.path.join(MODELS_DIR, "hybrid_rf_model.pkl")
PREPROCESSOR_PATH  = os.path.join(MODELS_DIR, "snp_preprocessor.pkl")
SESSION_DATA_PATH  = os.path.join(MODELS_DIR, "session_data.pkl")

# ── Dataset Schema ────────────────────────────────────────────────────────────
LINE_ID_COL = "Line"            # Primary key column in SNP CSV
SNP_PREFIX  = "SNP_"           # Column prefix for SNP markers
MISSING_ALLELE = "NN"          # Sentinel for missing genotype calls

YIELD_TARGET       = "Yield_t_ha"
CATEGORICAL_TARGETS = ["Disease_Resistance", "Drought_Tolerance", "Grain_Quality", "Maturity_Period"]

# Environmental feature columns (present in bundled dataset)
ENV_FEATURES = ["Rainfall_mm", "Temp_C", "Humidity_pct"]

# Allowed column names from a standalone Environmental CSV upload
ENV_CSV_ALIASES = {
    "temperature":   "Temp_C",
    "temp":          "Temp_C",
    "temp_c":        "Temp_C",
    "rainfall":      "Rainfall_mm",
    "rainfall_mm":   "Rainfall_mm",
    "humidity":      "Humidity_pct",
    "humidity_pct":  "Humidity_pct",
    "soil_ph":       "Soil_pH",
    "soil_moisture": "Soil_Moisture",
}

# Allowed column names from a standalone Phenotypic CSV upload
PHENO_CSV_ALIASES = {
    "parent":   LINE_ID_COL,
    "line":     LINE_ID_COL,
    "yield":    YIELD_TARGET,
    "yield_t_ha": YIELD_TARGET,
    "disease":  "Disease_Resistance",
    "disease_resistance": "Disease_Resistance",
    "drought":  "Drought_Tolerance",
    "drought_tolerance":  "Drought_Tolerance",
    "quality": "Grain_Quality",
    "grain_quality": "Grain_Quality",
    "maturity": "Maturity_Period",
    "maturity_period": "Maturity_Period",
}

# ── Model Hyperparameters ─────────────────────────────────────────────────────
RF_N_ESTIMATORS  = 200
RF_MAX_DEPTH     = None
RF_RANDOM_STATE  = 42
RF_N_JOBS        = -1       # Use all CPU cores

TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15

# ── Recommendation Engine ─────────────────────────────────────────────────────
TOP_N = 5

# Composite score weights (must sum to 1.0)
SCORING_WEIGHTS = {
    "yield":         0.35,
    "drought":       0.20,
    "disease":       0.15,
    "quality":       0.15,
    "maturity":      0.05,
    "compatibility": 0.10,
}

# Normalisation ceiling for continuous yield (t/ha)
YIELD_NORM_MAX = 15.0

# Categorical → numeric score mappings
DROUGHT_SCORES  = {"High": 1.0, "Medium": 0.5, "Low": 0.0}
DISEASE_SCORES  = {"Resistant": 1.0, "Moderate": 0.5, "Susceptible": 0.0}
QUALITY_SCORES  = {"Premium": 1.0, "Standard": 0.5, "Poor": 0.0}
MATURITY_SCORES = {"Early": 1.0, "Medium": 0.5, "Late": 0.0}

# Max pairs to evaluate in full-pipeline mode (safety cap for huge datasets)
MAX_PAIRS_TO_EVALUATE = 1_000_000

# Batch size for chunked prediction (controls peak RAM usage)
PREDICT_BATCH_SIZE = 10_000

# ── SHAP ─────────────────────────────────────────────────────────────────────
SHAP_MAX_SAMPLES        = 50    # Reduced from 200 for fast interactive TreeExplainer
SHAP_BACKGROUND_SAMPLES = 50    # Background sample size for TreeExplainer
SHAP_TOP_K_FEATURES     = 20    # Number of features shown in importance chart

# ── MongoDB & Auth ───────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/hybrid_crop")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-me")
