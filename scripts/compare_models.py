"""Compare Isolation Forest vs One-Class SVM on synthetic UEBA data.

Usage:
    python scripts/compare_models.py

Output:
    - Console table with metrics (precision, recall, f1, training time)
    - data/model_comparison.json with full results
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ml.model import AnomalyModel, OCSVMModel

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_logs.json"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "model_comparison.json"

ANOMALOUS_COUNTRIES = {
    "United States", "China", "Brazil", "Australia", "Nigeria",
    "North Korea", "Iran", "Germany", "United Kingdom", "Japan",
}


def extract_features(events: list[dict]) -> pd.DataFrame:
    """Extract ML features from raw event dicts."""
    records = []
    for e in events:
        ts = datetime.fromisoformat(e["timestamp"])
        records.append({
            "event_id": e["event_id"],
            "user_id": e["user_id"],
            "hour_of_day": ts.hour,
            "day_of_week": ts.weekday(),
            "minutes_from_midnight": ts.hour * 60 + ts.minute,
            "country_code": e["country"],
            "bytes_transferred": e["bytes_transferred"],
        })
    return pd.DataFrame(records)


def label_ground_truth(df: pd.DataFrame) -> np.ndarray:
    """Heuristic ground-truth labels: 1 = anomaly, 0 = normal."""
    mask = (
        (df["hour_of_day"] >= 5)
        & (df["hour_of_day"] <= 21)
        & (~df["country_code"].isin(ANOMALOUS_COUNTRIES))
        & (df["bytes_transferred"] <= 500_000_000)
    )
    return (~mask).astype(int).values


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute precision, recall, f1."""
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def main() -> None:
    """Entry point."""
    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} not found. Run scripts/generate_synthetic_logs.py first.")
        raise SystemExit(1)

    with open(DATA_PATH, encoding="utf-8") as f:
        events = json.load(f)

    print(f"Loaded {len(events)} events from {DATA_PATH}")

    df_all = extract_features(events)
    y_true = label_ground_truth(df_all)

    mask_normal = y_true == 0
    df_normal = df_all.loc[mask_normal].copy()

    print(f"Normal events for training: {len(df_normal)} / {len(df_all)}")

    results = {"dataset_size": len(df_all), "anomaly_ratio": float(y_true.mean()), "models": {}}

    # --- Isolation Forest ---
    print("\n--- Isolation Forest ---")
    if_model = AnomalyModel(contamination=0.05, random_state=42)

    t0 = time.perf_counter()
    if_model.train(df_normal)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    if_scores = if_model.predict(df_all)
    infer_time = time.perf_counter() - t0

    if_labels = (if_scores > 0.5).astype(int)
    if_metrics = compute_metrics(y_true, if_labels)

    print(f"  Train time: {train_time:.4f}s")
    print(f"  Infer time: {infer_time:.4f}s")
    print(f"  Precision:  {if_metrics['precision']:.4f}")
    print(f"  Recall:     {if_metrics['recall']:.4f}")
    print(f"  F1:         {if_metrics['f1']:.4f}")

    results["models"]["isolation_forest"] = {
        "train_time_seconds": round(train_time, 4),
        "infer_time_seconds": round(infer_time, 4),
        **if_metrics,
    }

    # --- One-Class SVM ---
    print("\n--- One-Class SVM ---")
    ocsvm_model = OCSVMModel(nu=0.05, kernel="rbf", gamma="auto", random_state=42)

    t0 = time.perf_counter()
    ocsvm_model.train(df_normal)
    ocsvm_train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    ocsvm_scores = ocsvm_model.predict(df_all)
    ocsvm_infer_time = time.perf_counter() - t0

    ocsvm_labels = (ocsvm_scores > 0.5).astype(int)
    ocsvm_metrics = compute_metrics(y_true, ocsvm_labels)

    print(f"  Train time: {ocsvm_train_time:.4f}s")
    print(f"  Infer time: {ocsvm_infer_time:.4f}s")
    print(f"  Precision:  {ocsvm_metrics['precision']:.4f}")
    print(f"  Recall:     {ocsvm_metrics['recall']:.4f}")
    print(f"  F1:         {ocsvm_metrics['f1']:.4f}")

    results["models"]["one_class_svm"] = {
        "train_time_seconds": round(ocsvm_train_time, 4),
        "infer_time_seconds": round(ocsvm_infer_time, 4),
        **ocsvm_metrics,
    }

    # --- Summary ---
    print("\n--- Summary ---")
    print(f"{'Metric':<20} {'Isolation Forest':<20} {'One-Class SVM':<20}")
    print("-" * 60)
    for metric in ["precision", "recall", "f1", "train_time_seconds", "infer_time_seconds"]:
        if_val = results["models"]["isolation_forest"][metric]
        ocsvm_val = results["models"]["one_class_svm"][metric]
        print(f"{metric:<20} {if_val:<20} {ocsvm_val:<20}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
