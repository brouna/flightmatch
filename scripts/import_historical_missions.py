"""Import historical missions from data/hist_missions.csv"""
import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.historical import FlightSource, FlightType, HistoricalFlight

BATCH_SIZE = 500


def parse_float(val: str) -> float | None:
    val = val.strip()
    return float(val) if val else None


def parse_int(val: str) -> int | None:
    val = val.strip()
    return int(val) if val else None


def parse_date(val: str):
    val = val.strip()
    if not val:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {val!r}")


def parse_bool(val: str) -> bool:
    return val.strip().upper() == "TRUE"


def parse_flight_type(val: str) -> str | None:
    val = val.strip().lower()
    if val in ("private", "commercial"):
        return val
    return None


async def import_missions(csv_path: str) -> None:
    inserted = 0
    errors = 0
    batch: list[HistoricalFlight] = []

    async with AsyncSessionLocal() as db:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for line_num, row in enumerate(reader, start=2):
                try:
                    pilot_id_raw = row["pilot_id"].strip()
                    if pilot_id_raw == "#N/A":
                        errors += 1
                        continue
                    origin = row["origin_airport"].strip()
                    destination = row["destination_airport"].strip()
                    flight_date = parse_date(row["Mission Date"])
                    if not origin or not destination or not flight_date:
                        print(f"Line {line_num}: skipping — missing required field")
                        errors += 1
                        continue
                    flight = HistoricalFlight(
                        pilot_id=int(pilot_id_raw) if pilot_id_raw else None,
                        aircraft_type=row["aircraft-type"].strip() or None,
                        origin_airport=origin,
                        destination_airport=destination,
                        flight_date=flight_date,
                        distance_nm=parse_float(row["distance_nm"]),
                        duration_h=parse_float(row["duration_h"]),
                        num_passengers=parse_int(row["Number of Passengers"]),
                        accepted=parse_bool(row["accepted"]),
                        flight_type=parse_flight_type(row["Type"]),
                        source=FlightSource.imported.value,
                    )
                    batch.append(flight)
                except Exception as e:
                    print(f"Line {line_num}: skipping — {e}")
                    errors += 1
                    continue

                if len(batch) >= BATCH_SIZE:
                    db.add_all(batch)
                    await db.commit()
                    inserted += len(batch)
                    print(f"  {inserted} rows inserted...")
                    batch = []

        if batch:
            db.add_all(batch)
            await db.commit()
            inserted += len(batch)

    print(f"Done: {inserted} inserted, {errors} errors")


if __name__ == "__main__":
    path = Path(__file__).parent.parent / "data" / "hist_missions.csv"
    asyncio.run(import_missions(str(path)))
