"""Orchestrates calendar sync for one integration."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.availability import CalendarIntegration, CalendarProvider, PilotAvailability, AvailabilitySource


async def sync_pilot(
    pilot_id: int,
    provider: CalendarProvider,
    db: AsyncSession,
) -> int:
    """Sync calendar for a specific pilot/provider. Returns number of events upserted."""
    result = await db.execute(
        select(CalendarIntegration).where(
            CalendarIntegration.pilot_id == pilot_id,
            CalendarIntegration.provider == provider,
            CalendarIntegration.sync_enabled == True,  # noqa: E712
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return 0

    cal_provider = _get_provider(provider)
    if cal_provider is None:
        return 0

    # Refresh token if expiring soon
    if integration.token_expires_at:
        expires = integration.token_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc) + timedelta(minutes=10):
            try:
                token_data = await cal_provider.refresh_token(integration)
                if token_data.get("access_token"):
                    from app.calendar_sync.encryption import encrypt_token
                    integration.access_token = encrypt_token(token_data["access_token"])
                    integration.token_expires_at = token_data.get("expires_at")
            except Exception:
                pass

    from_dt = datetime.now(timezone.utc)
    to_dt = from_dt + timedelta(days=90)

    try:
        events = await cal_provider.fetch_events(integration, from_dt, to_dt)
    except Exception:
        return 0

    # Upsert events: delete existing calendar-sourced entries, re-insert
    source_map = {
        CalendarProvider.google: AvailabilitySource.google,
        CalendarProvider.outlook: AvailabilitySource.outlook,
        CalendarProvider.apple: AvailabilitySource.apple,
    }
    source = source_map[provider]

    await db.execute(
        delete(PilotAvailability).where(
            PilotAvailability.pilot_id == pilot_id,
            PilotAvailability.source == source,
            PilotAvailability.start_time >= from_dt,
        )
    )

    count = 0
    seen_uids: set[str] = set()
    for event in events:
        if event.uid in seen_uids:
            continue
        seen_uids.add(event.uid)
        avail = PilotAvailability(
            pilot_id=pilot_id,
            start_time=event.start,
            end_time=event.end,
            source=source,
            is_busy=event.is_busy,
            calendar_uid=event.uid,
        )
        db.add(avail)
        count += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    await db.flush()
    return count


def _get_provider(provider: CalendarProvider):
    if provider == CalendarProvider.google:
        from app.calendar_sync.google import GoogleCalendarProvider
        return GoogleCalendarProvider()
    elif provider == CalendarProvider.outlook:
        from app.calendar_sync.outlook import OutlookCalendarProvider
        return OutlookCalendarProvider()
    elif provider == CalendarProvider.apple:
        from app.calendar_sync.apple import AppleCalendarProvider
        return AppleCalendarProvider()
    return None
