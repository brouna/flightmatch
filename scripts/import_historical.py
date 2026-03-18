"""CSV → historical_flights importer.

Expected CSV columns (case-insensitive):
  pilot_email (optional), aircraft_type, origin_airport, destination_airport,
  flight_date (YYYY-MM-DD), distance_nm, duration_h, accepted (true/false/1/0),
  outcome (completed|cancelled|no_show)

Usage:
    python scripts/import_historical.py path/to/flights.csv
"""
from __future__ import annotations

import asyncio
import csv
import sys
from datetime import date
from pathlib import Path


async def import_csv(file_path: str, db=None) -> int:
    from sqlalchemy import select
    from app.models import Pilot
    from app.models.historical import HistoricalFlight, FlightOutcome, FlightSource

    rows = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys
            r = {k.strip().lower(): v.strip() for k, v in row.items()}
            rows.append(r)

    close_db = False
    if db is None:
        from app.database import AsyncSessionLocal
        db = AsyncSessionLocal()
        close_db = True

    count = 0
    try:
        for r in rows:
            # Resolve pilot_id by email if provided
            pilot_id = None
            email = r.get("pilot_email") or r.get("email")
            if email:
                result = await db.execute(select(Pilot).where(Pilot.email == email))
                pilot = result.scalar_one_or_none()
                if pilot:
                    pilot_id = pilot.id

            # Parse flight_date
            flight_date_str = r.get("flight_date") or r.get("date")
            if not flight_date_str:
                continue
            flight_date = date.fromisoformat(flight_date_str)

            # Parse accepted
            accepted_str = r.get("accepted", "true").lower()
            accepted = accepted_str in ("true", "1", "yes")

            # Parse outcome
            outcome_str = r.get("outcome", "").lower()
            outcome = None
            if outcome_str:
                try:
                    outcome = FlightOutcome(outcome_str)
                except ValueError:
                    pass

            flight = HistoricalFlight(
                pilot_id=pilot_id,
                aircraft_type=r.get("aircraft_type", "unknown"),
                origin_airport=(r.get("origin_airport") or r.get("origin", "")).upper(),
                destination_airport=(r.get("destination_airport") or r.get("destination", "")).upper(),
                flight_date=flight_date,
                distance_nm=float(r["distance_nm"]) if r.get("distance_nm") else None,
                duration_h=float(r["duration_h"]) if r.get("duration_h") else None,
                accepted=accepted,
                outcome=outcome,
                source=FlightSource.imported,
            )
            db.add(flight)
            count += 1

        if not close_db:
            await db.flush()
        else:
            await db.commit()
    finally:
        if close_db:
            await db.close()

    return count


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_historical.py <path/to/flights.csv>")
        sys.exit(1)

    file_path = sys.argv[1]
    count = await import_csv(file_path)
    print(f"Imported {count} historical flights")


if __name__ == "__main__":
    asyncio.run(main())
