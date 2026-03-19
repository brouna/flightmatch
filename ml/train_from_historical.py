"""Bootstrap LightGBM training from historical_flights using synthetic negatives.

Since all historical rows are flights that actually happened (positives only),
we generate synthetic negatives by pairing each flight with random other pilots.
The model learns to distinguish pilots with genuine affinity for a route from
random ones.

Usage:
    python -m ml.train_from_historical
"""
from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "model.joblib"
FEATURE_ORDER_PATH = MODEL_DIR / "feature_order.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"

NEGATIVES_PER_POSITIVE = 4
RANDOM_SEED = 42

FEATURE_COLUMNS = [
    "origin_flight_count",
    "dest_flight_count",
    "route_flight_count",
    "inferred_home_dist_nm",
    "total_flights",
    "recency_days",
    "flight_type_match",
    "passenger_count_delta",
    "distance_delta_nm",
    "distance_nm",
    "num_passengers",
    "flight_type_private",
    "month",
    "monthly_activity_score",
]


async def _train_async() -> dict:
    import pandas as pd
    from sklearn.metrics import roc_auc_score
    import lightgbm as lgb

    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.historical import HistoricalFlight
    from app.matching.pilot_stats import compute_stats, build_pair_features

    print("Loading historical flights...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(HistoricalFlight))
        flights = list(result.scalars().all())

    print(f"  {len(flights)} flights loaded")

    # Compute per-pilot stats from all historical data
    all_stats = compute_stats(flights)
    pilot_ids = list(all_stats.keys())
    print(f"  {len(pilot_ids)} pilots with flight history")

    rng = random.Random(RANDOM_SEED)
    rows = []

    for flight in flights:
        if flight.pilot_id is None or flight.pilot_id not in all_stats:
            continue
        if flight.flight_date is None or not flight.origin_airport or not flight.destination_airport:
            continue

        pax = flight.num_passengers or 1
        flight_type = flight.flight_type or "private"
        month = flight.flight_date.month

        # Positive example
        pos_feats = build_pair_features(
            stats=all_stats[flight.pilot_id],
            origin=flight.origin_airport,
            destination=flight.destination_airport,
            num_passengers=pax,
            flight_type=flight_type,
            distance_nm=flight.distance_nm,
            month=month,
            reference_date=flight.flight_date,
        )
        pos_feats["label"] = 1
        rows.append(pos_feats)

        # Synthetic negatives: random other pilots
        other_pilots = [p for p in pilot_ids if p != flight.pilot_id]
        neg_sample = rng.sample(other_pilots, min(NEGATIVES_PER_POSITIVE, len(other_pilots)))
        for neg_pilot_id in neg_sample:
            neg_feats = build_pair_features(
                stats=all_stats[neg_pilot_id],
                origin=flight.origin_airport,
                destination=flight.destination_airport,
                num_passengers=pax,
                flight_type=flight_type,
                distance_nm=flight.distance_nm,
                month=month,
                reference_date=flight.flight_date,
            )
            neg_feats["label"] = 0
            rows.append(neg_feats)

    print(f"  {sum(1 for r in rows if r['label'] == 1)} positives, "
          f"{sum(1 for r in rows if r['label'] == 0)} negatives")

    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    split = int(len(df) * 0.8)
    X_train = df.iloc[:split][FEATURE_COLUMNS]
    y_train = df.iloc[:split]["label"]
    X_val = df.iloc[split:][FEATURE_COLUMNS]
    y_val = df.iloc[split:]["label"]

    print(f"Training on {len(X_train)} rows, validating on {len(X_val)} rows...")

    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        colsample_bytree=0.8,
        subsample=0.8,
        class_weight="balanced",
        random_state=RANDOM_SEED,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)],
    )

    y_pred = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, y_pred)
    print(f"Validation AUC: {auc:.4f}")

    # Feature importances
    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
    top = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print("Top features:")
    for feat, imp in top[:5]:
        print(f"  {feat}: {imp:.0f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(FEATURE_COLUMNS, FEATURE_ORDER_PATH)

    metadata = {
        "trained_at": datetime.utcnow().isoformat(),
        "source": "historical_flights",
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "auc": round(auc, 4),
        "feature_columns": FEATURE_COLUMNS,
        "feature_importances": importances,
        "negatives_per_positive": NEGATIVES_PER_POSITIVE,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    print(f"Model saved to {MODEL_PATH}")

    return metadata


def train() -> dict:
    return asyncio.run(_train_async())


if __name__ == "__main__":
    result = train()
    print(result)
