"""Google Calendar OAuth2 integration."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from app.calendar_sync.base import CalendarProvider, CalendarEvent
from app.config import get_settings

SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class GoogleCalendarProvider(CalendarProvider):
    def __init__(self):
        self.settings = get_settings()

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{AUTH_URL}?{query}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_at": expires_at,
            }

    async def refresh_token(self, integration) -> dict[str, Any]:
        from app.calendar_sync.encryption import decrypt_token
        refresh = decrypt_token(integration.refresh_token)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "refresh_token": refresh,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
            return {
                "access_token": data["access_token"],
                "refresh_token": refresh,
                "expires_at": expires_at,
            }

    async def fetch_events(
        self, integration, from_dt: datetime, to_dt: datetime
    ) -> list[CalendarEvent]:
        from app.calendar_sync.encryption import decrypt_token
        access_token = decrypt_token(integration.access_token)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                EVENTS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": from_dt.isoformat(),
                    "timeMax": to_dt.isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 500,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

        events = []
        for item in items:
            try:
                uid = item["id"]
                summary = item.get("summary", "Busy")
                start_str = item["start"].get("dateTime") or item["start"].get("date")
                end_str = item["end"].get("dateTime") or item["end"].get("date")
                start = datetime.fromisoformat(start_str)
                end = datetime.fromisoformat(end_str)
                events.append(CalendarEvent(uid=uid, summary=summary, start=start, end=end))
            except (KeyError, ValueError):
                continue
        return events
