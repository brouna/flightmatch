from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class PilotCreate(BaseModel):
    email: EmailStr
    name: str
    home_airport: str
    phone: str | None = None
    certifications: list[str] = []
    preferred_regions: list[str] = []
    max_range_nm: int | None = None
    active: bool = True


class PilotUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    home_airport: str | None = None
    phone: str | None = None
    certifications: list[str] | None = None
    preferred_regions: list[str] | None = None
    max_range_nm: int | None = None
    active: bool | None = None


class PilotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    home_airport: str
    phone: str | None
    certifications: list[str]
    preferred_regions: list[str]
    max_range_nm: int | None
    active: bool
    created_at: datetime
