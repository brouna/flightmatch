"""Import pilots from data/pilots.csv"""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.models.pilot import Pilot


async def import_pilots(csv_path: str) -> None:
    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row["Pilot_id"].strip():
                    continue
                pilot_id = int(row["Pilot_id"])
                name = row["Pilot_name"].strip()

                existing = await db.get(Pilot, pilot_id)
                if existing:
                    skipped += 1
                    continue

                pilot = Pilot(id=pilot_id, name=name)
                db.add(pilot)
                inserted += 1

        await db.commit()

    print(f"Done: {inserted} inserted, {skipped} skipped")


if __name__ == "__main__":
    path = Path(__file__).parent.parent / "data" / "pilots.csv"
    asyncio.run(import_pilots(str(path)))
