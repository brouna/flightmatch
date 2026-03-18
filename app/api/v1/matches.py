from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.deps import verify_api_key
from app.models import MatchLog
from app.models.matching import PilotResponse
from app.schemas.matching import MatchLogRead, MatchLogUpdate

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/respond")
async def respond_to_match(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle signed email response link (no API key required — public endpoint)."""
    from app.notifications.email import verify_response_token

    data = verify_response_token(token)
    if not data:
        raise HTTPException(status_code=400, detail="Invalid or expired response token")

    match_id = data["match_id"]
    response = PilotResponse(data["response"])

    result = await db.execute(select(MatchLog).where(MatchLog.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.pilot_response = response
    match.response_at = datetime.now(timezone.utc)
    await db.flush()

    return {"message": f"Response recorded: {response.value}"}


@router.get("/{match_id}", response_model=MatchLogRead)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(MatchLog).where(MatchLog.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.patch("/{match_id}", response_model=MatchLogRead)
async def update_match(
    match_id: int,
    body: MatchLogUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(MatchLog).where(MatchLog.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.pilot_response = body.pilot_response
    match.response_at = body.response_at or datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(match)
    return match
