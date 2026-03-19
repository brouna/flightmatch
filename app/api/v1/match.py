"""Pilot ranking endpoint — given a flight, return top pilots by predicted affinity."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Pilot
from app.matching.pilot_stats import load_stats, build_pair_features
from app.matching.scorer import score_candidates

router = APIRouter(tags=["match"])

TOP_N = 10


class RankedPilotResult(BaseModel):
    rank: int
    pilot_id: int
    pilot_name: str
    score: float
    features: dict


class MatchResponse(BaseModel):
    origin: str
    destination: str
    num_passengers: int
    flight_type: str
    distance_nm: float | None
    month: int
    scoring_method: Literal["ml", "heuristic"]
    top_pilots: list[RankedPilotResult]


@router.get("/match", response_model=MatchResponse)
async def match_pilots(
    origin: str = Query(..., description="Origin ICAO airport code"),
    destination: str = Query(..., description="Destination ICAO airport code"),
    num_passengers: int = Query(1, ge=1),
    flight_type: Literal["private", "commercial"] = Query("private"),
    distance_nm: float | None = Query(None, description="Mission distance (computed if omitted)"),
    month: int | None = Query(None, ge=1, le=12, description="Month (1-12); defaults to current month"),
    db: AsyncSession = Depends(get_db),
):
    origin = origin.upper().strip()
    destination = destination.upper().strip()

    # Resolve distance if not provided
    resolved_distance = distance_nm
    if resolved_distance is None:
        from app.matching.geo import airport_distance_nm
        resolved_distance = airport_distance_nm(origin, destination)

    resolved_month = month or date.today().month

    # Load all pilots
    result = await db.execute(select(Pilot).where(Pilot.active == True))  # noqa: E712
    pilots = list(result.scalars().all())

    # Load pilot stats from historical flights
    all_stats = await load_stats(db)

    # Build (pilot, features) pairs for all pilots
    candidates = []
    for pilot in pilots:
        stats = all_stats.get(pilot.id)
        if stats is None:
            # Pilot has no flight history — use zeroed features
            feats = {
                "origin_flight_count": 0.0,
                "dest_flight_count": 0.0,
                "route_flight_count": 0.0,
                "inferred_home_dist_nm": 999.0,
                "total_flights": 0.0,
                "recency_days": 730.0,
                "flight_type_match": 0.0,
                "passenger_count_delta": float(num_passengers),
                "distance_delta_nm": float(resolved_distance or 0),
                "distance_nm": float(resolved_distance or 0),
                "num_passengers": float(num_passengers),
                "flight_type_private": float(flight_type == "private"),
                "month": float(resolved_month),
                "monthly_activity_score": 0.0,
            }
        else:
            feats = build_pair_features(
                stats=stats,
                origin=origin,
                destination=destination,
                num_passengers=num_passengers,
                flight_type=flight_type,
                distance_nm=resolved_distance,
                month=resolved_month,
            )
        candidates.append((pilot, feats))

    # Score and rank
    from app.matching.scorer import _model, _load_model
    _load_model()
    scored = score_candidates(candidates)
    scoring_method: Literal["ml", "heuristic"] = "ml" if _model is not None else "heuristic"

    top = scored[:TOP_N]

    return MatchResponse(
        origin=origin,
        destination=destination,
        num_passengers=num_passengers,
        flight_type=flight_type,
        distance_nm=resolved_distance,
        month=resolved_month,
        scoring_method=scoring_method,
        top_pilots=[
            RankedPilotResult(
                rank=rank,
                pilot_id=pilot.id,
                pilot_name=pilot.name,
                score=round(score, 4),
                features=feats,
            )
            for rank, (pilot, score, feats) in enumerate(top, start=1)
        ],
    )
