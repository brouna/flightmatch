from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import verify_api_key
from app.models import Aircraft, Pilot
from app.models.aircraft import PilotAircraft
from app.schemas import AircraftCreate, AircraftUpdate, AircraftRead, PilotAircraftRead
from app.schemas.pilot import PilotRead

router = APIRouter(prefix="/aircraft", tags=["aircraft"])


async def get_aircraft_or_404(aircraft_id: int, db: AsyncSession) -> Aircraft:
    result = await db.execute(select(Aircraft).where(Aircraft.id == aircraft_id))
    aircraft = result.scalar_one_or_none()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return aircraft


@router.post("", response_model=AircraftRead, status_code=status.HTTP_201_CREATED)
async def create_aircraft(
    body: AircraftCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    aircraft = Aircraft(**body.model_dump())
    db.add(aircraft)
    await db.flush()
    await db.refresh(aircraft)
    return aircraft


@router.patch("/{aircraft_id}", response_model=AircraftRead)
async def update_aircraft(
    aircraft_id: int,
    body: AircraftUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    aircraft = await get_aircraft_or_404(aircraft_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(aircraft, field, value)
    await db.flush()
    await db.refresh(aircraft)
    return aircraft


@router.delete("/{aircraft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_aircraft(
    aircraft_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    aircraft = await get_aircraft_or_404(aircraft_id, db)
    aircraft.active = False
    await db.flush()


@router.post("/{aircraft_id}/pilots/{pilot_id}", status_code=status.HTTP_201_CREATED)
async def link_pilot_to_aircraft(
    aircraft_id: int,
    pilot_id: int,
    is_primary: bool = False,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_aircraft_or_404(aircraft_id, db)
    result = await db.execute(select(Pilot).where(Pilot.id == pilot_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pilot not found")

    existing = await db.execute(
        select(PilotAircraft).where(
            PilotAircraft.aircraft_id == aircraft_id,
            PilotAircraft.pilot_id == pilot_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Pilot already linked to aircraft")

    link = PilotAircraft(pilot_id=pilot_id, aircraft_id=aircraft_id, is_primary=is_primary)
    db.add(link)
    await db.flush()
    return {"message": "Pilot linked to aircraft"}


@router.delete("/{aircraft_id}/pilots/{pilot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_pilot_from_aircraft(
    aircraft_id: int,
    pilot_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(
        select(PilotAircraft).where(
            PilotAircraft.aircraft_id == aircraft_id,
            PilotAircraft.pilot_id == pilot_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.delete(link)
    await db.flush()


@router.get("/{aircraft_id}/pilots", response_model=list[PilotRead])
async def list_aircraft_pilots(
    aircraft_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_aircraft_or_404(aircraft_id, db)
    result = await db.execute(
        select(Pilot)
        .join(PilotAircraft)
        .where(PilotAircraft.aircraft_id == aircraft_id)
    )
    return result.scalars().all()
