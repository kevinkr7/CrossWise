"""
ml/models/model_registry.py — Factory for breeding model instances.

Add new model types here and they'll be available everywhere via
``get_model(name)``.
"""

from __future__ import annotations

from config import RF_N_ESTIMATORS, RF_MAX_DEPTH, RF_RANDOM_STATE, RF_N_JOBS
from ml.models.base_model import BaseBreedingModel
from ml.models.random_forest_model import RandomForestBreedingModel
# For simplicity, we just use the same multi-output wrapper logic for other models
# Let's import the models here, we'll wrap them similarly or just rely on RF as default.
from sklearn.ensemble import ExtraTreesRegressor, ExtraTreesClassifier
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
try:
    import lightgbm as lgb
    LGBM_AVAILABLE = True
except ImportError:
    LGBM_AVAILABLE = False

MODEL_REGISTRY: dict[str, type[BaseBreedingModel]] = {
    "random_forest": RandomForestBreedingModel,
}


def get_model(name: str = "random_forest", **kwargs) -> BaseBreedingModel:
    """
    Instantiate a breeding model by name.

    Parameters
    ----------
    name : str
        Key in ``MODEL_REGISTRY``.
    **kwargs
        Extra keyword arguments forwarded to the model constructor
        (override the config defaults).

    Returns
    -------
    BaseBreedingModel
        A fresh, un-fitted model instance.
    """
    if name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model '{name}'. Available: {list(MODEL_REGISTRY.keys())}"
        )

    cls = MODEL_REGISTRY[name]

    if cls is RandomForestBreedingModel:
        defaults = dict(
            n_estimators = RF_N_ESTIMATORS,
            max_depth    = RF_MAX_DEPTH,
            random_state = RF_RANDOM_STATE,
            n_jobs       = RF_N_JOBS,
        )
        defaults.update(kwargs)
        return cls(**defaults)

    return cls(**kwargs)
