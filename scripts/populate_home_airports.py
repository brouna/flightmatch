"""
One-off script to populate pilots.home_airport based on historical flight data.

For each pilot, counts how many times each airport appears across all their flights
(both as origin and destination), then sets home_airport to the most frequent one.

Only updates pilots where home_airport is currently NULL.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.pilot import Pilot
from app.models.historical import HistoricalFlight


async def populate_home_airports(dry_run: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        # Load all pilots without a home_airport, along with their historical flights
        result = await db.execute(
            select(Pilot)
            .where(Pilot.home_airport.is_(None))
            .options(selectinload(Pilot.historical_flights))
        )
        pilots = result.scalars().all()

        print(f"Found {len(pilots)} pilots with no home_airport set")

        updated = 0
        skipped_no_flights = 0

        for pilot in pilots:
            # Count every airport this pilot has flown from or to
            airport_counts: Counter = Counter()
            for flight in pilot.historical_flights:
                if flight.origin_airport:
                    airport_counts[flight.origin_airport.strip()] += 1
                if flight.destination_airport:
                    airport_counts[flight.destination_airport.strip()] += 1

            if not airport_counts:
                skipped_no_flights += 1
                continue

            home_airport, count = airport_counts.most_common(1)[0]
            print(f"  Pilot {pilot.id:>4} ({pilot.name:<30}) → {home_airport}  ({count} appearances)")

            if not dry_run:
                pilot.home_airport = home_airport
            updated += 1

        if not dry_run:
            await db.commit()
            print(f"\nDone: {updated} pilots updated, {skipped_no_flights} skipped (no flight history)")
        else:
            print(f"\nDry run — would update {updated} pilots, skip {skipped_no_flights} (no flight history)")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN — no changes will be saved ===\n")
    asyncio.run(populate_home_airports(dry_run=dry_run))
