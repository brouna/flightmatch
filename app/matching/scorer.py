"""ML scoring using LightGBM, with heuristic cold-start fallback."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np

MODEL_PATH = Path(__file__).parent.parent.parent / "ml" / "models" / "model.joblib"
FEATURE_ORDER_PATH = Path(__file__).parent.parent.parent / "ml" / "models" / "feature_order.joblib"

_model = None
_feature_order: list[str] | None = None


def _load_model():
    global _model, _feature_order
    if MODEL_PATH.exists() and FEATURE_ORDER_PATH.exists():
        try:
            _model = joblib.load(MODEL_PATH)
            _feature_order = joblib.load(FEATURE_ORDER_PATH)
        except Exception:
            _model = None
            _feature_order = None


def reload_model():
    global _model, _feature_order
    _model = None
    _feature_order = None
    _load_model()


def score_candidates(
    candidates: list[tuple[Any, dict[str, Any]]],  # (pilot, features)
) -> list[tuple[Any, float, dict[str, Any]]]:  # (pilot, score, features)
    """Score a list of (pilot, feature_dict) pairs. Returns sorted descending."""
    if not candidates:
        return []

    if _model is None:
        _load_model()

    if _model is not None and _feature_order is not None:
        return _score_with_model(candidates)
    else:
        return _score_heuristic(candidates)


def _score_with_model(candidates):
    import pandas as pd
    feature_dicts = [feats for _, feats in candidates]
    df = pd.DataFrame(feature_dicts)[_feature_order]
    probs = _model.predict_proba(df)[:, 1]
    scored = [(pilot, float(prob), feats) for (pilot, feats), prob in zip(candidates, probs)]
    return sorted(scored, key=lambda x: x[1], reverse=True)


def _score_heuristic(candidates):
    """Weighted heuristic fallback when no model is loaded."""
    max_home_dist = max(
        (f.get("inferred_home_dist_nm", f.get("ferry_distance_to_origin_nm", 0))
         for _, f in candidates),
        default=1,
    ) or 1

    scored = []
    for pilot, feats in candidates:
        home_dist = feats.get("inferred_home_dist_nm", feats.get("ferry_distance_to_origin_nm", 0))
        route_affinity = min(
            (feats.get("origin_flight_count", 0) + feats.get("dest_flight_count", 0)) / 10, 1.0
        )
        dist_score = 1.0 - (home_dist / max_home_dist)
        type_match = feats.get("flight_type_match", feats.get("region_match", 0))

        score = (dist_score * 0.6) + (route_affinity * 0.3) + (type_match * 0.1)
        score = max(0.0, min(1.0, score))
        scored.append((pilot, score, feats))

    return sorted(scored, key=lambda x: x[1], reverse=True)
