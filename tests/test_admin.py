"""Tests for admin endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_stats(client: AsyncClient, seed_data):
    resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "pilots" in data
    assert "missions" in data
    assert "matches" in data


@pytest.mark.asyncio
async def test_list_rules(client: AsyncClient, seed_data):
    resp = await client.get("/api/v1/admin/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert isinstance(rules, list)
    rule_keys = [r["rule_key"] for r in rules]
    assert "payload" in rule_keys
    assert "availability" in rule_keys


@pytest.mark.asyncio
async def test_toggle_rule(client: AsyncClient, seed_data):
    # Get rules first
    resp = await client.get("/api/v1/admin/rules")
    rules = resp.json()
    distance_rule = next(r for r in rules if r["rule_key"] == "distance")

    # Disable it
    resp = await client.patch(f"/api/v1/admin/rules/{distance_rule['id']}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    # Re-enable it
    resp = await client.patch(f"/api/v1/admin/rules/{distance_rule['id']}", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


@pytest.mark.asyncio
async def test_update_rule_parameters(client: AsyncClient, seed_data):
    resp = await client.get("/api/v1/admin/rules")
    rules = resp.json()
    distance_rule = next(r for r in rules if r["rule_key"] == "distance")

    resp = await client.patch(
        f"/api/v1/admin/rules/{distance_rule['id']}",
        json={"parameters": {"max_ferry_nm": 300}},
    )
    assert resp.status_code == 200
    assert resp.json()["parameters"]["max_ferry_nm"] == 300
