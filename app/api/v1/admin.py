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


@router.get("/model-metadata")
async def get_model_metadata(
    _: str = Depends(verify_api_key),
):
    """Return metadata for the currently deployed model."""
    import json
    from pathlib import Path
    metadata_path = Path(__file__).parent.parent.parent.parent / "ml" / "models" / "metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="No model trained yet")
    return json.loads(metadata_path.read_text())


@router.post("/retrain")
async def retrain_model(
    _: str = Depends(verify_api_key),
):
    """Trigger model retraining. Uses Celery if a worker is available, otherwise runs inline."""
    try:
        from app.tasks.celery_app import celery_app
        # Ping with a short timeout — only dispatch if a worker actually responds
        active = celery_app.control.ping(timeout=1.0)
        if active:
            from app.tasks.ml import retrain_model_task
            task = retrain_model_task.delay()
            return {"async": True, "task_id": task.id, "status": "pending"}
    except Exception:
        pass

    # No Celery worker available — run inline within the existing event loop.
    # Prefer real match response data; fall back to historical flights.
    from ml.train import _train_async
    result = await _train_async()
    if "error" in result:
        from ml.train_from_historical import _train_async as _train_historical
        result = await _train_historical()
    return {"async": False, "status": "complete", "result": result}


@router.get("/retrain/{task_id}")
async def get_retrain_status(
    task_id: str,
    _: str = Depends(verify_api_key),
):
    """Poll the status of an async retraining task."""
    try:
        from celery.result import AsyncResult
        from app.tasks.celery_app import celery_app
        result = AsyncResult(task_id, app=celery_app)
        if result.state == "PENDING":
            return {"status": "pending"}
        elif result.state == "STARTED":
            return {"status": "running"}
        elif result.state == "SUCCESS":
            return {"status": "complete", "result": result.get()}
        elif result.state == "FAILURE":
            return {"status": "failed", "error": str(result.result)}
        else:
            return {"status": result.state.lower()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
