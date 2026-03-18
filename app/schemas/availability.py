from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.availability import AvailabilitySource, CalendarProvider


class PilotAvailabilityCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    is_busy: bool = True
    source: AvailabilitySource = AvailabilitySource.manual


class PilotAvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pilot_id: int
    start_time: datetime
    end_time: datetime
    source: AvailabilitySource
    is_busy: bool
    calendar_uid: str | None


class CalendarIntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pilot_id: int
    provider: CalendarProvider
    calendar_id: str | None
    caldav_url: str | None
    last_synced_at: datetime | None
    sync_enabled: bool
    created_at: datetime
