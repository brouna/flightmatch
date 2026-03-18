"""Tests for pilot CRUD endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_pilot(client: AsyncClient):
    resp = await client.post("/api/v1/pilots", json={
        "email": "alice@example.com",
        "name": "Alice Smith",
        "home_airport": "KJFK",
        "certifications": ["MEL"],
        "preferred_regions": ["KE"],
        "active": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["home_airport"] == "KJFK"
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_get_pilot(client: AsyncClient, seed_data):
    pilot = seed_data["pilot"]
    resp = await client.get(f"/api/v1/pilots/{pilot.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pilot.id


@pytest.mark.asyncio
async def test_get_pilot_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/pilots/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_pilot(client: AsyncClient, seed_data):
    pilot = seed_data["pilot"]
    resp = await client.patch(f"/api/v1/pilots/{pilot.id}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_requires_api_key(client: AsyncClient):
    resp = await client.get("/api/v1/pilots/1", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_pilot_availability(client: AsyncClient, seed_data):
    from datetime import datetime, timezone, timedelta
    pilot = seed_data["pilot"]
    now = datetime.now(timezone.utc)
    resp = await client.post(f"/api/v1/pilots/{pilot.id}/availability", json={
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=4)).isoformat(),
        "is_busy": True,
        "source": "manual",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["pilot_id"] == pilot.id
    assert data["is_busy"] is True
