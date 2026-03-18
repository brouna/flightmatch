"""Test fixtures and database setup."""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import create_app
from app.database import Base, get_db
from app.config import get_settings

settings = get_settings()
TEST_DB_URL = settings.test_database_url


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine):
    """Provide a test database session with rollback after each test."""
    TestSession = async_sessionmaker(test_engine, expire_on_commit=False)
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db):
    """Provide an httpx AsyncClient wired to the test database."""
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": settings.api_key},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_data(db):
    """Seed test data: pilot + aircraft + mission."""
    from app.models import Pilot, Mission, MissionPassenger
    from app.models.aircraft import Aircraft, PilotAircraft
    from app.models.matching import MatchingRule

    pilot = Pilot(
        email="testpilot@example.com",
        name="Test Pilot",
        home_airport="KATL",
        certifications=[],
        preferred_regions=["K"],
        active=True,
    )
    db.add(pilot)

    aircraft = Aircraft(
        tail_number="N12345",
        make_model="Cessna 172",
        aircraft_type="SEL",
        range_nm=700,
        payload_lbs=800,
        num_seats=4,
        has_oxygen=False,
        ifr_equipped=True,
        fiki=False,
        is_accessible=False,
        home_airport="KATL",
        active=True,
    )
    db.add(aircraft)
    await db.flush()

    link = PilotAircraft(pilot_id=pilot.id, aircraft_id=aircraft.id, is_primary=True)
    db.add(link)

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    mission = Mission(
        title="Patient Transport: Atlanta to Charlotte",
        origin_airport="KATL",
        destination_airport="KCLT",
        earliest_departure=now + timedelta(days=3),
        latest_departure=now + timedelta(days=3, hours=4),
        estimated_duration_h=1.5,
        required_aircraft_type=[],
        min_range_nm=None,
    )
    db.add(mission)
    await db.flush()

    passenger = MissionPassenger(
        mission_id=mission.id,
        weight_lbs=150,
        bags_weight_lbs=30,
        requires_oxygen=False,
    )
    db.add(passenger)

    # Add default matching rules
    rules = [
        MatchingRule(name="Active Status", rule_key="active_status", enabled=True, parameters={}),
        MatchingRule(name="Payload", rule_key="payload", enabled=True, parameters={}),
        MatchingRule(name="Range", rule_key="range", enabled=True, parameters={}),
        MatchingRule(name="Seats", rule_key="seats", enabled=True, parameters={}),
        MatchingRule(name="Oxygen", rule_key="oxygen", enabled=True, parameters={}),
        MatchingRule(name="IFR", rule_key="ifr", enabled=True, parameters={}),
        MatchingRule(name="Accessibility", rule_key="accessibility", enabled=True, parameters={}),
        MatchingRule(name="Availability", rule_key="availability", enabled=True, parameters={}),
        MatchingRule(name="Distance", rule_key="distance", enabled=True, parameters={"max_ferry_nm": 500}),
        MatchingRule(name="Aircraft Type", rule_key="aircraft_type", enabled=True, parameters={}),
    ]
    for r in rules:
        db.add(r)

    await db.flush()

    # Invalidate rule cache
    from app.matching.hard_rules import invalidate_rules_cache
    invalidate_rules_cache()

    return {"pilot": pilot, "aircraft": aircraft, "mission": mission}
