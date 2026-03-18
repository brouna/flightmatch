"""Matching pipeline: hard rules → feature engineering → ML scoring → persist."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models import Pilot, Mission, MatchLog
from app.models.aircraft import Aircraft, PilotAircraft
from app.models.availability import PilotAvailability
from app.models.historical import HistoricalFlight
from app.matching.hard_rules import filter_pilots
from app.matching.feature_engineering import build_features
from app.matching.scorer import score_candidates
from app.schemas.matching import RankedPilot, RankedMission


async def run_match(
    mission_id: int,
    db: AsyncSession,
    persist: bool = False,
) -> list[RankedPilot]:
    """Full match pipeline for a mission. Returns ranked pilot list."""

    # 1. Load mission with passengers
    result = await db.execute(
        select(Mission)
        .where(Mission.id == mission_id)
        .options(selectinload(Mission.passengers))
    )
    mission = result.scalar_one_or_none()
    if not mission:
        return []
    passengers = mission.passengers

    # 2. Load all active pilots
    result = await db.execute(select(Pilot).where(Pilot.active == True))  # noqa: E712
    pilots = list(result.scalars().all())

    # 3. Load all pilot-aircraft links
    result = await db.execute(
        select(PilotAircraft).options(selectinload(PilotAircraft.aircraft))
    )
    links = result.scalars().all()
    pilot_aircraft_map: dict[int, list[Aircraft]] = {}
    for link in links:
        pilot_aircraft_map.setdefault(link.pilot_id, []).append(link.aircraft)

    # 4. Load busy availability blocks (is_busy=True)
    result = await db.execute(
        select(PilotAvailability).where(PilotAvailability.is_busy == True)  # noqa: E712
    )
    avail_rows = result.scalars().all()
    pilot_availability_map: dict[int, list[tuple[datetime, datetime]]] = {}
    for row in avail_rows:
        pilot_availability_map.setdefault(row.pilot_id, []).append(
            (row.start_time, row.end_time)
        )

    # 5. Hard-rule filtering
    passing = await filter_pilots(
        pilots, pilot_aircraft_map, pilot_availability_map, mission, passengers, db
    )

    # 6. Load historical flights for feature engineering
    result = await db.execute(select(HistoricalFlight))
    historical = list(result.scalars().all())

    # 7. Build features for passing pilots
    candidates = []
    for pilot, _ in passing:
        aircraft_list = pilot_aircraft_map.get(pilot.id, [])
        feats = build_features(pilot, aircraft_list, mission, passengers, historical)
        candidates.append((pilot, feats))

    # 8. Score and rank
    scored = score_candidates(candidates)

    # 9. Persist to match_logs if requested
    if persist:
        # Delete previous match logs for this mission
        await db.execute(delete(MatchLog).where(MatchLog.mission_id == mission_id))
        for rank, (pilot, score, feats) in enumerate(scored, start=1):
            log = MatchLog(
                mission_id=mission_id,
                pilot_id=pilot.id,
                matched_at=datetime.now(timezone.utc),
                hard_filter_pass=True,
                score=score,
                rank=rank,
                features_json=feats,
                notification_sent=False,
            )
            db.add(log)
        await db.flush()

    # 10. Build response
    ranked = []
    for rank, (pilot, score, feats) in enumerate(scored, start=1):
        # Get match_log_id if persisted
        match_log_id = 0
        if persist:
            result = await db.execute(
                select(MatchLog).where(
                    MatchLog.mission_id == mission_id,
                    MatchLog.pilot_id == pilot.id,
                )
            )
            log = result.scalar_one_or_none()
            match_log_id = log.id if log else 0

        ranked.append(
            RankedPilot(
                pilot_id=pilot.id,
                pilot_name=pilot.name,
                pilot_email=pilot.email,
                home_airport=pilot.home_airport,
                score=round(score, 4),
                rank=rank,
                hard_filter_pass=True,
                features=feats,
                match_log_id=match_log_id,
            )
        )

    return ranked


async def rank_missions_for_pilot(pilot_id: int, db: AsyncSession) -> list[RankedMission]:
    """Rank open missions by fit for a given pilot."""
    result = await db.execute(
        select(Pilot).where(Pilot.id == pilot_id)
    )
    pilot = result.scalar_one_or_none()
    if not pilot:
        return []

    from app.models.mission import MissionStatus
    result = await db.execute(
        select(Mission)
        .where(Mission.status == MissionStatus.open)
        .options(selectinload(Mission.passengers))
    )
    missions = list(result.scalars().all())

    # Get pilot's aircraft
    result = await db.execute(
        select(PilotAircraft)
        .where(PilotAircraft.pilot_id == pilot_id)
        .options(selectinload(PilotAircraft.aircraft))
    )
    aircraft_list = [link.aircraft for link in result.scalars().all()]

    result = await db.execute(select(HistoricalFlight).where(HistoricalFlight.pilot_id == pilot_id))
    historical = list(result.scalars().all())

    ranked = []
    for mission in missions:
        feats = build_features(pilot, aircraft_list, mission, mission.passengers, historical)
        # Use heuristic score
        from app.matching.scorer import _score_heuristic
        scored = _score_heuristic([(pilot, feats)])
        score = scored[0][1] if scored else 0.0
        ranked.append((mission, score, feats))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return [
        RankedMission(
            mission_id=m.id,
            title=m.title,
            origin_airport=m.origin_airport,
            destination_airport=m.destination_airport,
            earliest_departure=m.earliest_departure,
            score=round(s, 4),
            rank=i + 1,
            features=f,
        )
        for i, (m, s, f) in enumerate(ranked)
    ]
