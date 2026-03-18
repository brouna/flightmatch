"""Apple Calendar via CalDAV (app-specific password, no web OAuth)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.calendar_sync.base import CalendarProvider, CalendarEvent
from app.config import get_settings


class AppleCalendarProvider(CalendarProvider):
    def __init__(self):
        self.settings = get_settings()

    def get_authorization_url(self, state: str) -> str:
        # Apple uses app-specific passwords — no OAuth redirect URL
        raise NotImplementedError("Apple Calendar uses app-specific passwords, not OAuth")

    async def exchange_code(self, code: str) -> dict[str, Any]:
        raise NotImplementedError("Apple Calendar uses app-specific passwords")

    async def refresh_token(self, integration) -> dict[str, Any]:
        # App-specific passwords don't expire
        return {}

    async def fetch_events(
        self, integration, from_dt: datetime, to_dt: datetime
    ) -> list[CalendarEvent]:
        from app.calendar_sync.encryption import decrypt_token
        import caldav
        from vobject.icalendar import RecurringComponent

        username = integration.calendar_id  # stored as username
        password = decrypt_token(integration.access_token)
        caldav_url = integration.caldav_url or "https://caldav.icloud.com"

        client = caldav.DAVClient(
            url=caldav_url,
            username=username,
            password=password,
        )

        events = []
        try:
            principal = client.principal()
            calendars = principal.calendars()
            for cal in calendars:
                try:
                    cal_events = cal.date_search(start=from_dt, end=to_dt, expand=True)
                    for event in cal_events:
                        try:
                            vevent = event.vobject_instance.vevent
                            uid = str(vevent.uid.value)
                            summary = str(vevent.summary.value) if hasattr(vevent, "summary") else "Busy"
                            dtstart = vevent.dtstart.value
                            dtend = vevent.dtend.value if hasattr(vevent, "dtend") else from_dt
                            if not isinstance(dtstart, datetime):
                                dtstart = datetime.combine(dtstart, datetime.min.time())
                            if not isinstance(dtend, datetime):
                                dtend = datetime.combine(dtend, datetime.min.time())
                            events.append(
                                CalendarEvent(uid=uid, summary=summary, start=dtstart, end=dtend)
                            )
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass

        return events


async def connect_apple(
    pilot_id: int,
    username: str,
    app_password: str,
    caldav_url: str,
    db,
) -> None:
    """Store Apple CalDAV credentials (no OAuth flow needed)."""
    from app.models.availability import CalendarIntegration, CalendarProvider as CP
    from app.calendar_sync.encryption import encrypt_token
    from sqlalchemy import select

    result = await db.execute(
        select(CalendarIntegration).where(
            CalendarIntegration.pilot_id == pilot_id,
            CalendarIntegration.provider == CP.apple,
        )
    )
    integration = result.scalar_one_or_none()
    encrypted_pw = encrypt_token(app_password)

    if integration:
        integration.access_token = encrypted_pw
        integration.calendar_id = username
        integration.caldav_url = caldav_url
        integration.sync_enabled = True
    else:
        integration = CalendarIntegration(
            pilot_id=pilot_id,
            provider=CP.apple,
            access_token=encrypted_pw,
            calendar_id=username,
            caldav_url=caldav_url,
        )
        db.add(integration)
    await db.flush()
