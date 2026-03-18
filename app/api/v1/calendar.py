from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.deps import verify_api_key
from app.models import Pilot
from app.models.availability import CalendarIntegration, CalendarProvider
from app.schemas.availability import CalendarIntegrationRead

router = APIRouter(tags=["calendar"])


async def get_pilot_or_404(pilot_id: int, db: AsyncSession) -> Pilot:
    result = await db.execute(select(Pilot).where(Pilot.id == pilot_id))
    pilot = result.scalar_one_or_none()
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    return pilot


# ---- Google ----

@router.get("/pilots/{pilot_id}/calendar/google/authorize")
async def google_authorize(
    pilot_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_pilot_or_404(pilot_id, db)
    from app.calendar_sync.google import GoogleCalendarProvider
    provider = GoogleCalendarProvider()
    url = provider.get_authorization_url(state=str(pilot_id))
    return {"authorization_url": url}


@router.get("/calendar/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    pilot_id = int(state)
    await get_pilot_or_404(pilot_id, db)

    from app.calendar_sync.google import GoogleCalendarProvider
    provider = GoogleCalendarProvider()
    token_data = await provider.exchange_code(code)

    result = await db.execute(
        select(CalendarIntegration).where(
            CalendarIntegration.pilot_id == pilot_id,
            CalendarIntegration.provider == CalendarProvider.google,
        )
    )
    integration = result.scalar_one_or_none()
    if integration:
        integration.access_token = token_data["access_token"]
        integration.refresh_token = token_data.get("refresh_token")
        integration.token_expires_at = token_data.get("expires_at")
        integration.sync_enabled = True
    else:
        integration = CalendarIntegration(
            pilot_id=pilot_id,
            provider=CalendarProvider.google,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expires_at=token_data.get("expires_at"),
        )
        db.add(integration)
    await db.flush()
    return {"message": "Google Calendar connected"}


# ---- Outlook ----

@router.get("/pilots/{pilot_id}/calendar/outlook/authorize")
async def outlook_authorize(
    pilot_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_pilot_or_404(pilot_id, db)
    from app.calendar_sync.outlook import OutlookCalendarProvider
    provider = OutlookCalendarProvider()
    url = provider.get_authorization_url(state=str(pilot_id))
    return {"authorization_url": url}


@router.get("/calendar/outlook/callback")
async def outlook_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    pilot_id = int(state)
    await get_pilot_or_404(pilot_id, db)

    from app.calendar_sync.outlook import OutlookCalendarProvider
    provider = OutlookCalendarProvider()
    token_data = await provider.exchange_code(code)

    result = await db.execute(
        select(CalendarIntegration).where(
            CalendarIntegration.pilot_id == pilot_id,
            CalendarIntegration.provider == CalendarProvider.outlook,
        )
    )
    integration = result.scalar_one_or_none()
    if integration:
        integration.access_token = token_data["access_token"]
        integration.refresh_token = token_data.get("refresh_token")
        integration.token_expires_at = token_data.get("expires_at")
        integration.sync_enabled = True
    else:
        integration = CalendarIntegration(
            pilot_id=pilot_id,
            provider=CalendarProvider.outlook,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expires_at=token_data.get("expires_at"),
        )
        db.add(integration)
    await db.flush()
    return {"message": "Outlook Calendar connected"}


# ---- Generic provider management ----

@router.delete("/pilots/{pilot_id}/calendar/{provider}", status_code=204)
async def disconnect_calendar(
    pilot_id: int,
    provider: CalendarProvider,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_pilot_or_404(pilot_id, db)
    result = await db.execute(
        select(CalendarIntegration).where(
            CalendarIntegration.pilot_id == pilot_id,
            CalendarIntegration.provider == provider,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Calendar integration not found")
    await db.delete(integration)
    await db.flush()


@router.post("/pilots/{pilot_id}/calendar/{provider}/sync")
async def sync_calendar(
    pilot_id: int,
    provider: CalendarProvider,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    await get_pilot_or_404(pilot_id, db)
    from app.tasks.calendar import sync_pilot_calendar
    try:
        sync_pilot_calendar.delay(pilot_id, provider.value)
    except Exception:
        # Sync inline if Celery unavailable
        from app.calendar_sync.sync_service import sync_pilot
        await sync_pilot(pilot_id, provider, db)
    return {"message": f"Calendar sync initiated for {provider.value}"}
