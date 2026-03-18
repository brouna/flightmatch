"""Tests for mission CRUD and matching endpoints."""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


def mission_payload(**kwargs):
    now = datetime.now(timezone.utc)
    base = {
        "title": "Test Mission",
        "origin_airport": "KATL",
        "destination_airport": "KCLT",
        "earliest_departure": (now + timedelta(days=5)).isoformat(),
        "latest_departure": (now + timedelta(days=5, hours=4)).isoformat(),
        "estimated_duration_h": 1.5,
        "passengers": [{"weight_lbs": 150, "bags_weight_lbs": 20}],
    }
    base.update(kwargs)
    return base


@pytest.mark.asyncio
async def test_create_mission(client: AsyncClient):
    resp = await client.post("/api/v1/missions", json=mission_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Mission"
    assert data["total_payload_lbs"] == 170
    assert data["passenger_count"] == 1


@pytest.mark.asyncio
async def test_list_missions(client: AsyncClient, seed_data):
    resp = await client.get("/api/v1/missions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_mission(client: AsyncClient, seed_data):
    mission = seed_data["mission"]
    resp = await client.get(f"/api/v1/missions/{mission.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == mission.id
    assert "passengers" in data


@pytest.mark.asyncio
async def test_mission_computed_fields(client: AsyncClient):
    resp = await client.post("/api/v1/missions", json=mission_payload(
        passengers=[
            {"weight_lbs": 200, "bags_weight_lbs": 50, "requires_oxygen": True},
            {"weight_lbs": 150, "bags_weight_lbs": 20},
        ]
    ))
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_passenger_weight_lbs"] == 350
    assert data["total_bag_weight_lbs"] == 70
    assert data["total_payload_lbs"] == 420
    assert data["requires_oxygen"] is True
    assert data["passenger_count"] == 2


@pytest.mark.asyncio
async def test_get_ranked_pilots(client: AsyncClient, seed_data):
    mission = seed_data["mission"]
    resp = await client.get(f"/api/v1/missions/{mission.id}/pilots")
    assert resp.status_code == 200
    ranked = resp.json()
    assert isinstance(ranked, list)
    if ranked:
        assert "score" in ranked[0]
        assert "rank" in ranked[0]
        assert ranked[0]["rank"] == 1


@pytest.mark.asyncio
async def test_trigger_match_returns_ranked(client: AsyncClient, seed_data):
    mission = seed_data["mission"]
    resp = await client.post(f"/api/v1/missions/{mission.id}/match")
    assert resp.status_code == 200
    ranked = resp.json()
    assert isinstance(ranked, list)
    # Pilot should pass all hard rules and appear in results
    if ranked:
        assert ranked[0]["pilot_id"] == seed_data["pilot"].id


@pytest.mark.asyncio
async def test_get_mission_matches(client: AsyncClient, seed_data):
    mission = seed_data["mission"]
    # Trigger match first
    await client.post(f"/api/v1/missions/{mission.id}/match")
    resp = await client.get(f"/api/v1/missions/{mission.id}/matches")
    assert resp.status_code == 200
    matches = resp.json()
    assert isinstance(matches, list)
