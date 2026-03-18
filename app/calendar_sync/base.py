"""Abstract calendar provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CalendarEvent:
    uid: str
    summary: str
    start: datetime
    end: datetime
    is_busy: bool = True


class CalendarProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Return OAuth2 authorization URL."""

    @abstractmethod
    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange auth code for token dict with keys: access_token, refresh_token, expires_at."""

    @abstractmethod
    async def refresh_token(self, integration) -> dict[str, Any]:
        """Refresh access token. Returns updated token dict."""

    @abstractmethod
    async def fetch_events(self, integration, from_dt: datetime, to_dt: datetime) -> list[CalendarEvent]:
        """Fetch busy events in the given range."""
