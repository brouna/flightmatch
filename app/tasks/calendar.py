"""Celery tasks for calendar sync."""
import asyncio
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.calendar.sync_all_calendars")
def sync_all_calendars():
    """Fan out to sync all active calendar integrations."""
    asyncio.run(_sync_all_async())


@celery_app.task(name="app.tasks.calendar.sync_pilot_calendar")
def sync_pilot_calendar(pilot_id: int, provider_str: str):
    asyncio.run(_sync_pilot_async(pilot_id, provider_str))


async def _sync_all_async():
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.availability import CalendarIntegration
    from app.calendar_sync.sync_service import sync_pilot

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CalendarIntegration).where(CalendarIntegration.sync_enabled == True)  # noqa: E712
        )
        integrations = result.scalars().all()
        for integration in integrations:
            try:
                await sync_pilot(integration.pilot_id, integration.provider, db)
            except Exception:
                pass
        await db.commit()


async def _sync_pilot_async(pilot_id: int, provider_str: str):
    from app.database import AsyncSessionLocal
    from app.models.availability import CalendarProvider
    from app.calendar_sync.sync_service import sync_pilot

    provider = CalendarProvider(provider_str)
    async with AsyncSessionLocal() as db:
        await sync_pilot(pilot_id, provider, db)
        await db.commit()
