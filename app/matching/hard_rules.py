"""Hard-rule filtering for pilot-mission matching.

Rules are loaded from the matching_rules DB table (cached in memory).
Each rule function returns True if the pilot/aircraft PASSES the rule.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable, Any
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Pilot, Mission, MissionPassenger
from app.models.aircraft import Aircraft, PilotAircraft
from app.models.availability import PilotAvailability
from app.models.matching import MatchingRule
from app.matching.geo import airport_distance_nm

# ---- Rule registry ----

RuleFn = Callable[[Pilot, list[Aircraft], Mission, list[MissionPassenger], dict[str, Any]], bool]
_RULES: dict[str, RuleFn] = {}


def rule(key: str):
    def decorator(fn: RuleFn) -> RuleFn:
        _RULES[key] = fn
        return fn
    return decorator


# ---- Individual rules ----

@rule("active_status")
def rule_active_status(pilot, aircraft_list, mission, passengers, params) -> bool:
    return pilot.active and any(a.active for a in aircraft_list)


@rule("payload")
def rule_payload(pilot, aircraft_list, mission, passengers, params) -> bool:
    total = sum(p.weight_lbs + p.bags_weight_lbs for p in passengers)
    return any(a.payload_lbs >= total for a in aircraft_list if a.active)


@rule("range")
def rule_range(pilot, aircraft_list, mission, passengers, params) -> bool:
    if not mission.min_range_nm:
        return True
    return any(a.range_nm >= mission.min_range_nm for a in aircraft_list if a.active)


@rule("aircraft_type")
def rule_aircraft_type(pilot, aircraft_list, mission, passengers, params) -> bool:
    if not mission.required_aircraft_type:
        return True
    return any(a.aircraft_type in mission.required_aircraft_type for a in aircraft_list if a.active)


@rule("oxygen")
def rule_oxygen(pilot, aircraft_list, mission, passengers, params) -> bool:
    if not any(p.requires_oxygen for p in passengers):
        return True
    return any(a.has_oxygen for a in aircraft_list if a.active)


@rule("ifr")
def rule_ifr(pilot, aircraft_list, mission, passengers, params) -> bool:
    # All pilots are IFR certified per spec; check aircraft equipment
    return any(a.ifr_equipped for a in aircraft_list if a.active)


@rule("seats")
def rule_seats(pilot, aircraft_list, mission, passengers, params) -> bool:
    n = len(passengers)
    return any(a.num_seats >= n for a in aircraft_list if a.active)


@rule("accessibility")
def rule_accessibility(pilot, aircraft_list, mission, passengers, params) -> bool:
    from app.models.mission import MobilityEquipment
    needs_access = any(p.mobility_equipment != MobilityEquipment.none for p in passengers)
    if not needs_access:
        return True
    return any(a.is_accessible for a in aircraft_list if a.active)


@rule("availability")
def rule_availability(pilot, aircraft_list, mission, passengers, params) -> bool:
    # _availability_blocks must be injected into params by the engine
    busy_blocks: list[tuple[datetime, datetime]] = params.get("_busy_blocks", [])
    m_start = mission.earliest_departure
    m_end = mission.latest_departure
    for start, end in busy_blocks:
        # Overlap check
        if start < m_end and end > m_start:
            return False
    return True


@rule("distance")
def rule_distance(pilot, aircraft_list, mission, passengers, params) -> bool:
    max_ferry_nm: float = params.get("max_ferry_nm", 500)
    dist = airport_distance_nm(pilot.home_airport, mission.origin_airport)
    if dist is None:
        return True  # Unknown airport — don't filter
    return dist <= max_ferry_nm


# ---- Cache / load from DB ----

_rules_cache: list[MatchingRule] | None = None


def invalidate_rules_cache():
    global _rules_cache
    _rules_cache = None


async def load_enabled_rules(db: AsyncSession) -> list[MatchingRule]:
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache
    result = await db.execute(
        select(MatchingRule).where(MatchingRule.enabled == True).order_by(MatchingRule.id)  # noqa: E712
    )
    _rules_cache = list(result.scalars().all())
    return _rules_cache


# ---- Main filter function ----

async def filter_pilots(
    pilots: list[Pilot],
    pilot_aircraft_map: dict[int, list[Aircraft]],
    pilot_availability_map: dict[int, list[tuple[datetime, datetime]]],
    mission: Mission,
    passengers: list[MissionPassenger],
    db: AsyncSession,
) -> list[tuple[Pilot, dict]]:
    """
    Returns list of (pilot, failure_reasons) where failure_reasons is empty on pass.
    Only pilots that pass ALL enabled rules are returned (failure_reasons == {}).
    """
    enabled_rules = await load_enabled_rules(db)

    passing: list[tuple[Pilot, dict]] = []
    for pilot in pilots:
        aircraft_list = pilot_aircraft_map.get(pilot.id, [])
        busy_blocks = pilot_availability_map.get(pilot.id, [])
        failures: dict[str, str] = {}

        for rule_row in enabled_rules:
            fn = _RULES.get(rule_row.rule_key)
            if fn is None:
                continue
            params = dict(rule_row.parameters or {})
            if rule_row.rule_key == "availability":
                params["_busy_blocks"] = busy_blocks

            try:
                passed = fn(pilot, aircraft_list, mission, passengers, params)
            except Exception as e:
                passed = True  # Don't filter on rule error — log and move on
                continue

            if not passed:
                failures[rule_row.rule_key] = f"Failed rule: {rule_row.name}"

        if not failures:
            passing.append((pilot, {}))

    return passing
