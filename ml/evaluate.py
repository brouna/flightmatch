"""Evaluate model on held-out data and print metrics."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

MODEL_PATH = Path(__file__).parent / "models" / "model.joblib"
FEATURE_ORDER_PATH = Path(__file__).parent / "models" / "feature_order.joblib"
METADATA_PATH = Path(__file__).parent / "models" / "metadata.json"


def evaluate():
    if not MODEL_PATH.exists():
        print("No model found. Run ml/train.py first.")
        return

    model = joblib.load(MODEL_PATH)
    feature_order = joblib.load(FEATURE_ORDER_PATH)

    if METADATA_PATH.exists():
        metadata = json.loads(METADATA_PATH.read_text())
        print(f"Model trained at: {metadata.get('trained_at')}")
        print(f"Training rows: {metadata.get('train_rows')}")
        print(f"Validation AUC: {metadata.get('auc')}")
        print(f"Features: {metadata.get('feature_columns')}")

    print("\nFeature importances:")
    importances = model.feature_importances_
    for feat, imp in sorted(zip(feature_order, importances), key=lambda x: -x[1]):
        print(f"  {feat}: {imp:.1f}")


if __name__ == "__main__":
    evaluate()
