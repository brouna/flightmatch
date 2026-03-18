"""Offline LightGBM training script.

Usage:
    python -m ml.train

Pulls training data from the database, trains a binary classifier predicting
whether a pilot will accept + complete a mission, and saves the model artifact.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "model.joblib"
FEATURE_ORDER_PATH = MODEL_DIR / "feature_order.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"

FEATURE_COLUMNS = [
    "distance_origin_to_dest_nm",
    "ferry_distance_to_origin_nm",
    "aircraft_range_margin",
    "total_humanitarian_flights",
    "completion_rate",
    "flights_similar_distance",
    "recency_days",
    "acceptance_rate",
    "region_match",
    "home_airport_distance_nm",
    "duration_h",
    "requires_oxygen",
    "has_mobility_equipment",
    "total_payload_lbs",
    "day_of_week",
    "advance_notice_days",
    "month",
    "fiki",
]


def train() -> dict:
    """Train LightGBM model from match_logs + historical_flights. Returns metrics dict."""
    return asyncio.run(_train_async())


async def _train_async() -> dict:
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score
    import lightgbm as lgb

    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models import MatchLog, HistoricalFlight

    async with AsyncSessionLocal() as db:
        # Build training set from match_logs with features_json
        result = await db.execute(
            select(MatchLog).where(
                MatchLog.features_json.isnot(None),
                MatchLog.pilot_response.in_(["accepted", "declined"]),
            )
        )
        logs = result.scalars().all()

    rows = []
    for log in logs:
        feats = log.features_json or {}
        label = 1 if log.pilot_response.value == "accepted" else 0
        row = {col: feats.get(col, 0.0) for col in FEATURE_COLUMNS}
        row["label"] = label
        rows.append(row)

    if len(rows) < 50:
        return {"error": "Not enough training data", "rows": len(rows)}

    df = pd.DataFrame(rows)
    # Time-ordered split (no leakage)
    split = int(len(df) * 0.8)
    X_train = df.iloc[:split][FEATURE_COLUMNS]
    y_train = df.iloc[:split]["label"]
    X_val = df.iloc[split:][FEATURE_COLUMNS]
    y_val = df.iloc[split:]["label"]

    model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=10,
        colsample_bytree=0.8,
        subsample=0.8,
        random_state=42,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(0)],
    )

    y_pred = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, y_pred)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(FEATURE_COLUMNS, FEATURE_ORDER_PATH)

    metadata = {
        "trained_at": datetime.utcnow().isoformat(),
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "auc": round(auc, 4),
        "feature_columns": FEATURE_COLUMNS,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    return metadata


if __name__ == "__main__":
    result = train()
    print(result)
