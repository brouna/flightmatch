from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from app.models.historical import FlightOutcome, FlightSource


class HistoricalFlightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pilot_id: int | None
    aircraft_type: str
    origin_airport: str
    destination_airport: str
    flight_date: date
    distance_nm: float | None
    duration_h: float | None
    accepted: bool
    outcome: FlightOutcome | None
    source: FlightSource
    created_at: datetime
