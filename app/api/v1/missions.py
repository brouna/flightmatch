from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import verify_api_key
from app.models import Mission, MissionPassenger, MatchLog
from app.models.mission import MissionStatus
from app.schemas import MissionCreate, MissionUpdate, MissionRead, MissionListRead
from app.schemas.matching import RankedPilot, MatchLogRead

router = APIRouter(prefix="/missions", tags=["missions"])


async def get_mission_or_404(mission_id: int, db: AsyncSession) -> Mission:
    result = await db.execute(
        select(Mission)
        .where(Mission.id == mission_id)
        .options(selectinload(Mission.passengers))
    )
    mission = result.scalar_one_or_none()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.post("", response_model=MissionRead, status_code=status.HTTP_201_CREATED)
async def create_mission(
    body: MissionCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    passengers = body.passengers
    mission_data = body.model_dump(exclude={"passengers"})
    mission = Mission(**mission_data)
    db.add(mission)
    await db.flush()

    for p in passengers:
        passenger = MissionPassenger(mission_id=mission.id, **p.model_dump())
        db.add(passenger)

    await db.flush()
    await db.refresh(mission)

    result = await db.execute(
        select(Mission)
        .where(Mission.id == mission.id)
        .options(selectinload(Mission.passengers))
    )
    return result.scalar_one()


@router.get("", response_model=list[MissionListRead])
async def list_missions(
    status: MissionStatus | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    q = select(Mission).order_by(Mission.earliest_departure)
    if status:
        q = q.where(Mission.status == status)
    if from_date:
        q = q.where(Mission.earliest_departure >= from_date)
    if to_date:
        q = q.where(Mission.earliest_departure <= to_date)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{mission_id}", response_model=MissionRead)
async def get_mission(
    mission_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    return await get_mission_or_404(mission_id, db)


@router.patch("/{mission_id}", response_model=MissionRead)
async def update_mission(
    mission_id: int,
    body: MissionUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    mission = await get_mission_or_404(mission_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(mission, field, value)
    await db.flush()
    await db.refresh(mission)
    result = await db.execute(
        select(Mission)
        .where(Mission.id == mission.id)
        .options(selectinload(Mission.passengers))
    )
    return result.scalar_one()


@router.get("/{mission_id}/pilots", response_model=list[RankedPilot])
async def get_ranked_pilots(
    mission_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Return pilots ranked by likelihood of being able to fly this mission."""
    from app.matching.pipeline import run_match
    await get_mission_or_404(mission_id, db)
    return await run_match(mission_id, db, persist=False)


@router.post("/{mission_id}/match", response_model=list[RankedPilot])
async def trigger_match(
    mission_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Run matching, persist results, and send email notifications."""
    from app.matching.pipeline import run_match
    from app.tasks.notifications import send_match_notifications

    await get_mission_or_404(mission_id, db)
    ranked = await run_match(mission_id, db, persist=True)

    # Kick off email notifications via Celery (non-blocking)
    try:
        send_match_notifications.delay(mission_id)
    except Exception:
        pass  # Celery may not be running in all environments

    return ranked


@router.get("/{mission_id}/matches", response_model=list[MatchLogRead])
async def get_mission_matches(
    mission_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_mission_or_404(mission_id, db)
    result = await db.execute(
        select(MatchLog)
        .where(MatchLog.mission_id == mission_id)
        .order_by(MatchLog.rank)
    )
    return result.scalars().all()
