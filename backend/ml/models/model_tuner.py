import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.ensemble import ExtraTreesRegressor, ExtraTreesClassifier
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.metrics import r2_score, accuracy_score
import joblib
import logging

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

logger = logging.getLogger(__name__)

def tune_and_compare(X, y_dict):
    """
    Compare multiple models and perform hyperparameter tuning using cross-validation.
    Returns the best model configurations.
    """
    results = {}
    
    # ── Yield Regression ──────────────────────────────────────────────────────
    if "yield" in y_dict:
        print("Evaluating Regression Models (Yield)...")
        y_yield = y_dict["yield"]
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        
        regressors = {
            "RandomForest": RandomForestRegressor(random_state=42),
            "ExtraTrees": ExtraTreesRegressor(random_state=42),
            "GradientBoosting": GradientBoostingRegressor(random_state=42),
        }
        if XGB_AVAILABLE:
            regressors["XGBoost"] = xgb.XGBRegressor(random_state=42, objective="reg:squarederror")
        if LGBM_AVAILABLE:
            regressors["LightGBM"] = lgb.LGBMRegressor(random_state=42)
            
        best_r2 = -float("inf")
        best_reg = None
        
        for name, reg in regressors.items():
            r2_scores = []
            for train_idx, val_idx in kf.split(X):
                reg.fit(X[train_idx], y_yield[train_idx])
                preds = reg.predict(X[val_idx])
                r2_scores.append(r2_score(y_yield[val_idx], preds))
            avg_r2 = np.mean(r2_scores)
            print(f"  {name} K-Fold R2: {avg_r2:.4f}")
            if avg_r2 > best_r2:
                best_r2 = avg_r2
                best_reg = name
                
        print(f"Best Regressor: {best_reg} (R2={best_r2:.4f})")
        results["best_regressor"] = best_reg

        # Tune best regressor (if it's RF for example, otherwise tune whatever won)
        if best_reg == "RandomForest":
            param_grid = {
                "n_estimators": [100, 200, 300],
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
                "max_features": ["sqrt", "log2", None]
            }
            search = RandomizedSearchCV(RandomForestRegressor(random_state=42), param_grid, n_iter=10, cv=5, scoring='r2', n_jobs=-1, random_state=42)
            search.fit(X, y_yield)
            print(f"Tuned {best_reg} Best R2: {search.best_score_:.4f}")
            print(f"Best Params: {search.best_params_}")
            results["regressor_params"] = search.best_params_
        else:
            results["regressor_params"] = {} # Can implement tuning for others if needed

    # ── Classification ────────────────────────────────────────────────────────
    best_clf_params = {}
    for target in y_dict:
        if target == "yield":
            continue
        print(f"\nEvaluating Classification Models ({target})...")
        y_cat = y_dict[target]
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        
        classifiers = {
            "RandomForest": RandomForestClassifier(random_state=42),
            "ExtraTrees": ExtraTreesClassifier(random_state=42),
            "GradientBoosting": GradientBoostingClassifier(random_state=42),
        }
        if XGB_AVAILABLE:
            classifiers["XGBoost"] = xgb.XGBClassifier(random_state=42, use_label_encoder=False, eval_metric="mlogloss")
        if LGBM_AVAILABLE:
            classifiers["LightGBM"] = lgb.LGBMClassifier(random_state=42)
            
        best_acc = -float("inf")
        best_clf = None
        
        for name, clf in classifiers.items():
            acc_scores = []
            for train_idx, val_idx in skf.split(X, y_cat):
                clf.fit(X[train_idx], y_cat[train_idx])
                preds = clf.predict(X[val_idx])
                acc_scores.append(accuracy_score(y_cat[val_idx], preds))
            avg_acc = np.mean(acc_scores)
            print(f"  {name} K-Fold Acc: {avg_acc:.4f}")
            if avg_acc > best_acc:
                best_acc = avg_acc
                best_clf = name
                
        print(f"Best Classifier for {target}: {best_clf} (Acc={best_acc:.4f})")
        
        # Tune RF if it won
        if best_clf == "RandomForest":
            param_grid = {
                "n_estimators": [100, 200, 300],
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
                "max_features": ["sqrt", "log2", None]
            }
            search = RandomizedSearchCV(RandomForestClassifier(random_state=42), param_grid, n_iter=10, cv=5, scoring='accuracy', n_jobs=-1, random_state=42)
            search.fit(X, y_cat)
            print(f"Tuned {best_clf} Best Acc: {search.best_score_:.4f}")
            print(f"Best Params: {search.best_params_}")
            best_clf_params[target] = search.best_params_
            
    results["classifier_params"] = best_clf_params
    return results

if __name__ == "__main__":
    from ml.preprocessor import SNPPreprocessor
    from config import current_dataset_path, UPLOAD_DIR, MAIZE_DATASET_PATH
    import pandas as pd
    
    path = current_dataset_path(UPLOAD_DIR, MAIZE_DATASET_PATH)
    df = pd.read_csv(path)
    # Drop rows where all targets are missing
    from config import YIELD_TARGET, CATEGORICAL_TARGETS
    target_cols = [YIELD_TARGET] + CATEGORICAL_TARGETS
    available_targets = [c for c in target_cols if c in df.columns]
    df = df.dropna(subset=available_targets)
    
    preprocessor = SNPPreprocessor()
    X, y = preprocessor.fit_transform(df)
    
    tune_and_compare(X, y)
