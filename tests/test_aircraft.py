"""Tests for aircraft CRUD endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_aircraft(client: AsyncClient):
    resp = await client.post("/api/v1/aircraft", json={
        "tail_number": "N99TEST",
        "make_model": "Piper PA-28",
        "aircraft_type": "SEL",
        "range_nm": 500,
        "payload_lbs": 600,
        "num_seats": 4,
        "has_oxygen": False,
        "ifr_equipped": True,
        "fiki": False,
        "is_accessible": False,
        "home_airport": "KORD",
        "active": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["tail_number"] == "N99TEST"


@pytest.mark.asyncio
async def test_update_aircraft(client: AsyncClient, seed_data):
    aircraft = seed_data["aircraft"]
    resp = await client.patch(f"/api/v1/aircraft/{aircraft.id}", json={"has_oxygen": True})
    assert resp.status_code == 200
    assert resp.json()["has_oxygen"] is True


@pytest.mark.asyncio
async def test_link_pilot_to_aircraft(client: AsyncClient, seed_data):
    # Create a second aircraft to link
    resp = await client.post("/api/v1/aircraft", json={
        "tail_number": "N88LINK",
        "make_model": "Beechcraft Bonanza",
        "aircraft_type": "SEL",
        "range_nm": 900,
        "payload_lbs": 900,
        "num_seats": 5,
        "has_oxygen": True,
        "ifr_equipped": True,
        "fiki": True,
        "is_accessible": False,
        "home_airport": "KATL",
        "active": True,
    })
    aircraft_id = resp.json()["id"]
    pilot = seed_data["pilot"]

    resp = await client.post(f"/api/v1/aircraft/{aircraft_id}/pilots/{pilot.id}")
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/pilots/{pilot.id}/aircraft")
    assert resp.status_code == 200
    tail_numbers = [a["aircraft"]["tail_number"] for a in resp.json()]
    assert "N88LINK" in tail_numbers


@pytest.mark.asyncio
async def test_deactivate_aircraft(client: AsyncClient, seed_data):
    aircraft = seed_data["aircraft"]
    resp = await client.delete(f"/api/v1/aircraft/{aircraft.id}")
    assert resp.status_code == 204
