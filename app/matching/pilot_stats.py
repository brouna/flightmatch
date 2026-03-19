"""Compute per-pilot aggregate stats from historical flights.

These stats are the basis for both ML training features and live inference.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.historical import HistoricalFlight
from app.matching.geo import airport_distance_nm


class PilotStats(TypedDict):
    pilot_id: int
    total_flights: int
    inferred_home_airport: str | None
    origin_counts: dict[str, int]
    dest_counts: dict[str, int]
    route_counts: dict[tuple[str, str], int]
    avg_passengers: float
    avg_distance_nm: float
    flight_type_private_pct: float
    last_flight_date: date | None
    monthly_activity: dict[int, int]  # month (1-12) -> count


def compute_stats(flights: list[HistoricalFlight]) -> dict[int, PilotStats]:
    """Build a stats dict keyed by pilot_id from a flat list of flights."""
    from collections import defaultdict

    buckets: dict[int, list[HistoricalFlight]] = defaultdict(list)
    for f in flights:
        if f.pilot_id is not None:
            buckets[f.pilot_id].append(f)

    result: dict[int, PilotStats] = {}
    for pilot_id, pf in buckets.items():
        origin_counts: Counter[str] = Counter(f.origin_airport for f in pf)
        dest_counts: Counter[str] = Counter(f.destination_airport for f in pf)
        route_counts: Counter[tuple[str, str]] = Counter(
            (f.origin_airport, f.destination_airport) for f in pf
        )

        # Inferred home: airport with highest max(origin_count, dest_count)
        all_airports = set(origin_counts) | set(dest_counts)
        inferred_home = max(
            all_airports,
            key=lambda a: max(origin_counts.get(a, 0), dest_counts.get(a, 0)),
            default=None,
        )

        pax_vals = [f.num_passengers for f in pf if f.num_passengers is not None]
        dist_vals = [f.distance_nm for f in pf if f.distance_nm is not None]
        private_count = sum(1 for f in pf if f.flight_type == "private")

        monthly: Counter[int] = Counter(
            f.flight_date.month for f in pf if f.flight_date is not None
        )

        last_date = max(
            (f.flight_date for f in pf if f.flight_date is not None),
            default=None,
        )

        result[pilot_id] = PilotStats(
            pilot_id=pilot_id,
            total_flights=len(pf),
            inferred_home_airport=inferred_home,
            origin_counts=dict(origin_counts),
            dest_counts=dict(dest_counts),
            route_counts={f"{o}:{d}": c for (o, d), c in route_counts.items()},
            avg_passengers=sum(pax_vals) / len(pax_vals) if pax_vals else 1.0,
            avg_distance_nm=sum(dist_vals) / len(dist_vals) if dist_vals else 0.0,
            flight_type_private_pct=private_count / len(pf),
            last_flight_date=last_date,
            monthly_activity=dict(monthly),
        )

    return result


async def load_stats(db: AsyncSession) -> dict[int, PilotStats]:
    """Load all historical flights from DB and compute pilot stats."""
    result = await db.execute(select(HistoricalFlight))
    flights = list(result.scalars().all())
    return compute_stats(flights)


def build_pair_features(
    stats: PilotStats,
    origin: str,
    destination: str,
    num_passengers: int,
    flight_type: str,  # "private" or "commercial"
    distance_nm: float | None,
    month: int,
    reference_date: date | None = None,
) -> dict[str, float]:
    """Compute feature vector for one (pilot, flight) pair."""
    from datetime import date as date_type

    today = reference_date or date_type.today()

    origin_count = stats["origin_counts"].get(origin, 0)
    dest_count = stats["dest_counts"].get(destination, 0)
    route_key = f"{origin}:{destination}"
    route_count = stats["route_counts"].get(route_key, 0)

    # Distance from inferred home to mission origin
    home = stats["inferred_home_airport"]
    home_dist = airport_distance_nm(home, origin) if home else None
    home_dist_nm = home_dist if home_dist is not None else 999.0

    # Recency
    last = stats["last_flight_date"]
    recency_days = (today - last).days if last else 730

    # Flight type match
    private_pct = stats["flight_type_private_pct"]
    pilot_dominant_private = private_pct >= 0.5
    mission_private = flight_type == "private"
    flight_type_match = int(pilot_dominant_private == mission_private)

    # Passenger delta
    pax_delta = abs(num_passengers - stats["avg_passengers"])

    # Distance delta
    dist_nm = distance_nm or 0.0
    dist_delta = abs(dist_nm - stats["avg_distance_nm"])

    # Seasonal activity
    max_monthly = max(stats["monthly_activity"].values(), default=1)
    monthly_score = stats["monthly_activity"].get(month, 0) / max_monthly

    return {
        "origin_flight_count": float(origin_count),
        "dest_flight_count": float(dest_count),
        "route_flight_count": float(route_count),
        "inferred_home_dist_nm": home_dist_nm,
        "total_flights": float(stats["total_flights"]),
        "recency_days": float(recency_days),
        "flight_type_match": float(flight_type_match),
        "passenger_count_delta": pax_delta,
        "distance_delta_nm": dist_delta,
        "distance_nm": dist_nm,
        "num_passengers": float(num_passengers),
        "flight_type_private": float(int(mission_private)),
        "month": float(month),
        "monthly_activity_score": monthly_score,
    }
