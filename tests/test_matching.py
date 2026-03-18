"""Tests for matching engine hard rules and scoring."""
import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_hard_rules_pass_valid_pilot(db, seed_data):
    from app.models import Pilot, Mission
    from app.models.aircraft import PilotAircraft, Aircraft
    from app.matching.hard_rules import filter_pilots
    from app.matching.hard_rules import invalidate_rules_cache
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    invalidate_rules_cache()

    pilot = seed_data["pilot"]
    mission = seed_data["mission"]

    result = await db.execute(
        select(Mission).where(Mission.id == mission.id)
        .options(selectinload(Mission.passengers))
    )
    mission = result.scalar_one()

    result = await db.execute(
        select(PilotAircraft)
        .where(PilotAircraft.pilot_id == pilot.id)
        .options(selectinload(PilotAircraft.aircraft))
    )
    aircraft_list = [link.aircraft for link in result.scalars().all()]
    pilot_aircraft_map = {pilot.id: aircraft_list}
    pilot_availability_map = {pilot.id: []}

    passing = await filter_pilots(
        [pilot], pilot_aircraft_map, pilot_availability_map,
        mission, mission.passengers, db
    )
    assert len(passing) == 1
    assert passing[0][0].id == pilot.id


@pytest.mark.asyncio
async def test_hard_rules_fail_payload(db, seed_data):
    from app.models import Mission
    from app.models.mission import MissionPassenger, MobilityEquipment
    from app.matching.hard_rules import filter_pilots, invalidate_rules_cache
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    invalidate_rules_cache()

    pilot = seed_data["pilot"]
    aircraft = seed_data["aircraft"]

    # Create a mission with heavy payload
    now = datetime.now(timezone.utc)
    mission = Mission(
        title="Heavy Payload Test",
        origin_airport="KATL",
        destination_airport="KCLT",
        earliest_departure=now + timedelta(days=3),
        latest_departure=now + timedelta(days=3, hours=4),
        estimated_duration_h=1.5,
        required_aircraft_type=[],
    )
    db.add(mission)
    await db.flush()

    # Passenger heavier than aircraft payload
    passenger = MissionPassenger(
        mission_id=mission.id,
        weight_lbs=900,  # exceeds aircraft.payload_lbs=800
        bags_weight_lbs=0,
        requires_oxygen=False,
    )
    db.add(passenger)
    await db.flush()

    result = await db.execute(
        select(Mission).where(Mission.id == mission.id)
        .options(selectinload(Mission.passengers))
    )
    mission = result.scalar_one()

    pilot_aircraft_map = {pilot.id: [aircraft]}
    pilot_availability_map = {pilot.id: []}

    passing = await filter_pilots(
        [pilot], pilot_aircraft_map, pilot_availability_map,
        mission, mission.passengers, db
    )
    assert len(passing) == 0  # Should fail payload rule


@pytest.mark.asyncio
async def test_hard_rules_fail_availability(db, seed_data):
    from app.models import Mission
    from app.matching.hard_rules import filter_pilots, invalidate_rules_cache
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    invalidate_rules_cache()

    pilot = seed_data["pilot"]
    aircraft = seed_data["aircraft"]
    mission = seed_data["mission"]

    result = await db.execute(
        select(Mission).where(Mission.id == mission.id)
        .options(selectinload(Mission.passengers))
    )
    mission = result.scalar_one()

    # Mark pilot as busy during the entire mission window
    busy_blocks = [(mission.earliest_departure - timedelta(hours=1),
                    mission.latest_departure + timedelta(hours=1))]
    pilot_aircraft_map = {pilot.id: [aircraft]}
    pilot_availability_map = {pilot.id: busy_blocks}

    passing = await filter_pilots(
        [pilot], pilot_aircraft_map, pilot_availability_map,
        mission, mission.passengers, db
    )
    assert len(passing) == 0  # Should fail availability rule


def test_heuristic_scorer():
    from app.matching.scorer import _score_heuristic

    class FakePilot:
        id = 1

    p = FakePilot()
    candidates = [
        (p, {
            "ferry_distance_to_origin_nm": 50.0,
            "completion_rate": 0.9,
            "region_match": 1,
            "advance_notice_days": 7,
        }),
        (p, {
            "ferry_distance_to_origin_nm": 400.0,
            "completion_rate": 0.5,
            "region_match": 0,
            "advance_notice_days": 2,
        }),
    ]
    scored = _score_heuristic(candidates)
    assert scored[0][1] > scored[1][1]  # Closer pilot scores higher
    assert 0.0 <= scored[0][1] <= 1.0


def test_feature_engineering():
    from app.matching.feature_engineering import build_features

    class FakePilot:
        id = 1
        home_airport = "KATL"
        preferred_regions = ["K"]

    class FakeAircraft:
        range_nm = 700
        fiki = False

    class FakePassenger:
        weight_lbs = 150
        bags_weight_lbs = 30
        requires_oxygen = False
        from app.models.mission import MobilityEquipment
        mobility_equipment = MobilityEquipment.none

    class FakeMission:
        origin_airport = "KATL"
        destination_airport = "KCLT"
        estimated_duration_h = 1.5
        earliest_departure = datetime.now(timezone.utc) + timedelta(days=7)

    feats = build_features(FakePilot(), [FakeAircraft()], FakeMission(), [FakePassenger()], [])
    assert "distance_origin_to_dest_nm" in feats
    assert "completion_rate" in feats
    assert feats["requires_oxygen"] == 0
    assert feats["total_payload_lbs"] == 180
