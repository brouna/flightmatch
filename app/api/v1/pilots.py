from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import verify_api_key
from app.models import Pilot, Mission, MatchLog
from app.schemas import PilotCreate, PilotUpdate, PilotRead, PilotAvailabilityCreate, PilotAvailabilityRead
from app.schemas.aircraft import PilotAircraftRead
from app.schemas.matching import RankedMission
from app.models.availability import PilotAvailability
from app.models.aircraft import PilotAircraft

router = APIRouter(prefix="/pilots", tags=["pilots"])


async def get_pilot_or_404(pilot_id: int, db: AsyncSession) -> Pilot:
    result = await db.execute(select(Pilot).where(Pilot.id == pilot_id))
    pilot = result.scalar_one_or_none()
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    return pilot


@router.post("", response_model=PilotRead, status_code=status.HTTP_201_CREATED)
async def create_pilot(
    body: PilotCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    from sqlalchemy.exc import IntegrityError
    pilot = Pilot(**body.model_dump())
    db.add(pilot)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A pilot with that email already exists")
    await db.refresh(pilot)
    return pilot


@router.get("/{pilot_id}", response_model=PilotRead)
async def get_pilot(
    pilot_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    return await get_pilot_or_404(pilot_id, db)


@router.patch("/{pilot_id}", response_model=PilotRead)
async def update_pilot(
    pilot_id: int,
    body: PilotUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    pilot = await get_pilot_or_404(pilot_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pilot, field, value)
    await db.flush()
    await db.refresh(pilot)
    return pilot


@router.get("/{pilot_id}/aircraft", response_model=list[PilotAircraftRead])
async def list_pilot_aircraft(
    pilot_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_pilot_or_404(pilot_id, db)
    result = await db.execute(
        select(PilotAircraft)
        .where(PilotAircraft.pilot_id == pilot_id)
        .options(selectinload(PilotAircraft.aircraft))
    )
    return result.scalars().all()


@router.get("/{pilot_id}/availability", response_model=list[PilotAvailabilityRead])
async def get_pilot_availability(
    pilot_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_pilot_or_404(pilot_id, db)
    result = await db.execute(
        select(PilotAvailability)
        .where(PilotAvailability.pilot_id == pilot_id)
        .order_by(PilotAvailability.start_time)
    )
    return result.scalars().all()


@router.post("/{pilot_id}/availability", response_model=PilotAvailabilityRead, status_code=201)
async def create_availability_block(
    pilot_id: int,
    body: PilotAvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_pilot_or_404(pilot_id, db)
    avail = PilotAvailability(pilot_id=pilot_id, **body.model_dump())
    db.add(avail)
    await db.flush()
    await db.refresh(avail)
    return avail


@router.get("/{pilot_id}/missions", response_model=list[RankedMission])
async def get_ranked_missions_for_pilot(
    pilot_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Return open missions ranked by fit for this pilot."""
    from app.matching.pipeline import rank_missions_for_pilot
    await get_pilot_or_404(pilot_id, db)
    return await rank_missions_for_pilot(pilot_id, db)
