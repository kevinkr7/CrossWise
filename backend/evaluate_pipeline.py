import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from ml.trainer import load_trained_artefacts, train_model
from ml.predictor import predict_batch, compute_confidence_for_top
from config import CATEGORICAL_TARGETS, UPLOAD_DIR, MAIZE_DATASET_PATH, YIELD_TARGET
from utils.io_utils import current_dataset_path
import itertools

def main():
    print("Training model to get fresh artefacts...")
    train_model()
    artefacts = load_trained_artefacts()
    if artefacts is None:
        print("Failed to train and load artefacts.")
        return

    model = artefacts["model"]
    session = artefacts["session"]
    X_test = session["X_test"]
    y_test = session["y_test"]

    print("Evaluating Regression Metrics (Yield)...")
    y_pred_yield = model.regressor.predict(X_test)
    mae = mean_absolute_error(y_test["yield"], y_pred_yield)
    rmse = np.sqrt(mean_squared_error(y_test["yield"], y_pred_yield))
    r2 = r2_score(y_test["yield"], y_pred_yield)

    print("Evaluating Classification Metrics...")
    acc_list, prec_list, rec_list, f1_list = [], [], [], []
    for target, clf in model.classifiers.items():
        if target in y_test:
            y_pred = clf.predict(X_test)
            acc_list.append(accuracy_score(y_test[target], y_pred))
            prec_list.append(precision_score(y_test[target], y_pred, average="macro", zero_division=0))
            rec_list.append(recall_score(y_test[target], y_pred, average="macro", zero_division=0))
            f1_list.append(f1_score(y_test[target], y_pred, average="macro", zero_division=0))
    
    avg_acc = np.mean(acc_list)
    avg_prec = np.mean(prec_list)
    avg_rec = np.mean(rec_list)
    avg_f1 = np.mean(f1_list)

    print("Evaluating Recommendation Time and Confidence...")
    snp_matrix = session["snp_matrix"]
    line_ids = session["line_ids"]
    
    # We evaluate for a subset of pairs to measure time and confidence
    num_lines = min(200, len(line_ids)) # Take up to 200 lines to form pairs
    pair_indices = np.array(list(itertools.combinations(range(num_lines), 2)))
    # Sample up to 10000 pairs to measure average time accurately
    if len(pair_indices) > 10000:
        indices = np.random.choice(len(pair_indices), 10000, replace=False)
        pair_indices = pair_indices[indices]
    
    n_pairs = len(pair_indices)
    env_vector = artefacts["preprocessor"].normalised_env_vector()
    
    start_time = time.time()
    results = predict_batch(
        pair_indices=pair_indices,
        line_ids=line_ids,
        snp_matrix=snp_matrix,
        env_vector=env_vector,
        model=model,
        preprocessor=artefacts["preprocessor"],
        label_encoders=None,
        chunk_size=10000
    )
    end_time = time.time()
    
    # Measure time per 100,000 pairs or something, let's just get average time per prediction
    total_time = end_time - start_time
    avg_time_per_pair = total_time / n_pairs if n_pairs > 0 else 0
    avg_recommendation_time = total_time # Time taken for a standard batch, or maybe the user wants time per pair

    # Confidence for top 100
    results.sort(key=lambda x: x["predicted_yield"], reverse=True)
    top_100 = results[:100]
    top_100_with_conf = compute_confidence_for_top(top_100, snp_matrix, env_vector, model, artefacts["preprocessor"])
    avg_conf = np.mean([r.get("confidence", 0) for r in top_100_with_conf])

    print("\n-------------------------------------------------")
    print("| Metric                            | Obtained Value |")
    print("| --------------------------------- | -------------: |")
    print(f"| MAE                               | {mae:14.4f} |")
    print(f"| RMSE                              | {rmse:14.4f} |")
    print(f"| R² Score                          | {r2:14.4f} |")
    print(f"| Classification Accuracy           | {avg_acc:14.4f} |")
    print(f"| Precision                         | {avg_prec:14.4f} |")
    print(f"| Recall                            | {avg_rec:14.4f} |")
    print(f"| F1-Score                          | {avg_f1:14.4f} |")
    print(f"| Average Recommendation Confidence | {avg_conf:14.4f} |")
    print(f"| Average Recommendation Time       | {total_time:9.4f} sec |") # Adjust this if they want time per pair
    print("-------------------------------------------------")

if __name__ == '__main__':
    main()
