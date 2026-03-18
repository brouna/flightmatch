from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AircraftCreate(BaseModel):
    tail_number: str
    make_model: str
    aircraft_type: str
    range_nm: int
    payload_lbs: int
    num_seats: int
    has_oxygen: bool = False
    ifr_equipped: bool = True
    fiki: bool = False
    is_accessible: bool = False
    accessibility_notes: str | None = None
    home_airport: str
    active: bool = True


class AircraftUpdate(BaseModel):
    make_model: str | None = None
    aircraft_type: str | None = None
    range_nm: int | None = None
    payload_lbs: int | None = None
    num_seats: int | None = None
    has_oxygen: bool | None = None
    ifr_equipped: bool | None = None
    fiki: bool | None = None
    is_accessible: bool | None = None
    accessibility_notes: str | None = None
    home_airport: str | None = None
    active: bool | None = None


class AircraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tail_number: str
    make_model: str
    aircraft_type: str
    range_nm: int
    payload_lbs: int
    num_seats: int
    has_oxygen: bool
    ifr_equipped: bool
    fiki: bool
    is_accessible: bool
    accessibility_notes: str | None
    home_airport: str
    active: bool
    created_at: datetime


class PilotAircraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pilot_id: int
    aircraft_id: int
    is_primary: bool
    notes: str | None
    aircraft: AircraftRead
