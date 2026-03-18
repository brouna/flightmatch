from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.deps import verify_api_key
from app.models import Pilot, Mission, MatchLog, HistoricalFlight
from app.models import MatchingRule
from app.models.mission import MissionStatus
from app.schemas.matching import MatchingRuleRead, MatchingRuleUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    total_pilots = (await db.execute(select(func.count(Pilot.id)))).scalar()
    active_pilots = (await db.execute(select(func.count(Pilot.id)).where(Pilot.active == True))).scalar()  # noqa: E712
    total_missions = (await db.execute(select(func.count(Mission.id)))).scalar()
    open_missions = (
        await db.execute(select(func.count(Mission.id)).where(Mission.status == MissionStatus.open))
    ).scalar()
    total_matches = (await db.execute(select(func.count(MatchLog.id)))).scalar()
    total_flights = (await db.execute(select(func.count(HistoricalFlight.id)))).scalar()

    recent_matches = await db.execute(
        select(MatchLog).order_by(MatchLog.matched_at.desc()).limit(10)
    )

    return {
        "pilots": {"total": total_pilots, "active": active_pilots},
        "missions": {"total": total_missions, "open": open_missions},
        "matches": {"total": total_matches},
        "historical_flights": total_flights,
        "recent_match_logs": [
            {
                "id": m.id,
                "mission_id": m.mission_id,
                "pilot_id": m.pilot_id,
                "score": float(m.score) if m.score else None,
                "rank": m.rank,
                "pilot_response": m.pilot_response.value,
                "matched_at": m.matched_at.isoformat(),
            }
            for m in recent_matches.scalars()
        ],
    }


@router.post("/import")
async def import_historical(
    file_path: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Import historical flights from a CSV file path."""
    from scripts.import_historical import import_csv
    try:
        count = await import_csv(file_path, db)
        return {"imported": count}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retrain")
async def retrain_model(
    _: str = Depends(verify_api_key),
):
    """Trigger model retraining via Celery."""
    from app.tasks.ml import retrain_model_task
    try:
        task = retrain_model_task.delay()
        return {"task_id": task.id, "message": "Retraining started"}
    except Exception:
        # Run inline if Celery unavailable
        from ml.train import train
        result = train()
        return {"message": "Retraining complete", "result": result}


@router.get("/rules", response_model=list[MatchingRuleRead])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(MatchingRule).order_by(MatchingRule.id))
    return result.scalars().all()


@router.patch("/rules/{rule_id}", response_model=MatchingRuleRead)
async def update_rule(
    rule_id: int,
    body: MatchingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(MatchingRule).where(MatchingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    await db.refresh(rule)

    # Invalidate rule cache
    from app.matching.hard_rules import invalidate_rules_cache
    invalidate_rules_cache()

    return rule
