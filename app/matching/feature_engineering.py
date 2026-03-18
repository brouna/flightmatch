"""Feature engineering for ML scoring."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models import Pilot, Mission, MissionPassenger
from app.models.aircraft import Aircraft
from app.models.historical import HistoricalFlight
from app.matching.geo import airport_distance_nm


def build_features(
    pilot: Pilot,
    aircraft_list: list[Aircraft],
    mission: Mission,
    passengers: list[MissionPassenger],
    historical_flights: list[HistoricalFlight],
) -> dict[str, Any]:
    """Compute feature vector for one pilot-mission pair."""
    now = datetime.now(timezone.utc)

    # --- Distance features ---
    dist_origin_to_dest = airport_distance_nm(
        mission.origin_airport, mission.destination_airport
    ) or 0.0
    ferry_dist = airport_distance_nm(pilot.home_airport, mission.origin_airport) or 0.0

    best_aircraft_range = max((a.range_nm for a in aircraft_list), default=0)
    aircraft_range_margin = best_aircraft_range - dist_origin_to_dest

    # --- Pilot history ---
    pilot_flights = [f for f in historical_flights if f.pilot_id == pilot.id]
    total_flights = len(pilot_flights)
    completed = [f for f in pilot_flights if f.outcome and f.outcome.value == "completed"]
    completion_rate = len(completed) / total_flights if total_flights else 0.5

    recent_flight = max((f.flight_date for f in pilot_flights), default=None)
    recency_days = (now.date() - recent_flight).days if recent_flight else 365

    accepted_flights = [f for f in pilot_flights if f.accepted]
    acceptance_rate = len(accepted_flights) / total_flights if total_flights else 0.5

    similar_dist_flights = [
        f for f in pilot_flights
        if f.distance_nm and abs(f.distance_nm - dist_origin_to_dest) < 100
    ]

    # --- Preference / region match ---
    region_match = 0
    if pilot.preferred_regions:
        origin_region = mission.origin_airport[:2]  # rough: use first 2 chars of ICAO
        dest_region = mission.destination_airport[:2]
        region_match = int(
            any(r in origin_region or r in dest_region for r in pilot.preferred_regions)
        )

    home_dist = airport_distance_nm(pilot.home_airport, mission.origin_airport) or ferry_dist

    # --- Mission context ---
    total_payload = sum(p.weight_lbs + p.bags_weight_lbs for p in passengers)
    requires_oxygen = any(p.requires_oxygen for p in passengers)
    from app.models.mission import MobilityEquipment
    has_mobility = any(p.mobility_equipment != MobilityEquipment.none for p in passengers)

    departure = mission.earliest_departure
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    advance_notice_days = max(0, (departure - now).days)

    # --- Aircraft capability ---
    best_fiki = any(a.fiki for a in aircraft_list)

    return {
        # Distance
        "distance_origin_to_dest_nm": dist_origin_to_dest,
        "ferry_distance_to_origin_nm": ferry_dist,
        "aircraft_range_margin": aircraft_range_margin,
        # Pilot history
        "total_humanitarian_flights": total_flights,
        "completion_rate": completion_rate,
        "flights_similar_distance": len(similar_dist_flights),
        "recency_days": recency_days,
        "acceptance_rate": acceptance_rate,
        # Preference match
        "region_match": region_match,
        "home_airport_distance_nm": home_dist,
        # Mission context
        "duration_h": mission.estimated_duration_h,
        "requires_oxygen": int(requires_oxygen),
        "has_mobility_equipment": int(has_mobility),
        "total_payload_lbs": total_payload,
        "day_of_week": departure.weekday(),
        "advance_notice_days": advance_notice_days,
        "month": departure.month,
        # Aircraft capability
        "fiki": int(best_fiki),
    }
