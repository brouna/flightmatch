"""Outlook Calendar via MSAL + Microsoft Graph API."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from app.calendar_sync.base import CalendarProvider, CalendarEvent
from app.config import get_settings

GRAPH_CALENDAR_URL = "https://graph.microsoft.com/v1.0/me/calendarView"


class OutlookCalendarProvider(CalendarProvider):
    def __init__(self):
        self.settings = get_settings()

    def get_authorization_url(self, state: str) -> str:
        try:
            import msal
            app = msal.PublicClientApplication(
                client_id=self.settings.outlook_client_id,
                authority=self.settings.outlook_authority,
            )
            # PKCE flow
            result = app.initiate_auth_code_flow(
                scopes=["Calendars.Read"],
                redirect_uri=self.settings.outlook_redirect_uri,
                state=state,
            )
            return result["auth_uri"]
        except ImportError:
            # Fallback manual URL construction
            params = {
                "client_id": self.settings.outlook_client_id,
                "response_type": "code",
                "redirect_uri": self.settings.outlook_redirect_uri,
                "scope": "Calendars.Read offline_access",
                "state": state,
            }
            query = "&".join(f"{k}={v}" for k, v in params.items())
            return f"{self.settings.outlook_authority}/oauth2/v2.0/authorize?{query}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        token_url = f"{self.settings.outlook_authority}/oauth2/v2.0/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "code": code,
                    "client_id": self.settings.outlook_client_id,
                    "client_secret": self.settings.outlook_client_secret,
                    "redirect_uri": self.settings.outlook_redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": "Calendars.Read offline_access",
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
        token_url = f"{self.settings.outlook_authority}/oauth2/v2.0/token"
        refresh = decrypt_token(integration.refresh_token)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "refresh_token": refresh,
                    "client_id": self.settings.outlook_client_id,
                    "client_secret": self.settings.outlook_client_secret,
                    "grant_type": "refresh_token",
                    "scope": "Calendars.Read offline_access",
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
                GRAPH_CALENDAR_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Prefer": 'outlook.timezone="UTC"',
                },
                params={
                    "startDateTime": from_dt.isoformat(),
                    "endDateTime": to_dt.isoformat(),
                    "$select": "id,subject,start,end,showAs",
                    "$top": "500",
                },
            )
            resp.raise_for_status()
            items = resp.json().get("value", [])

        events = []
        for item in items:
            try:
                uid = item["id"]
                summary = item.get("subject", "Busy")
                start = datetime.fromisoformat(item["start"]["dateTime"])
                end = datetime.fromisoformat(item["end"]["dateTime"])
                is_busy = item.get("showAs", "busy") != "free"
                if is_busy:
                    events.append(CalendarEvent(uid=uid, summary=summary, start=start, end=end))
            except (KeyError, ValueError):
                continue
        return events
