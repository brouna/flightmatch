from datetime import datetime
from pydantic import BaseModel, ConfigDict, computed_field
from app.models.mission import MissionStatus, MobilityEquipment


class MissionPassengerCreate(BaseModel):
    weight_lbs: int
    bags_weight_lbs: int = 0
    requires_oxygen: bool = False
    mobility_equipment: MobilityEquipment = MobilityEquipment.none
    mobility_notes: str | None = None


class MissionPassengerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    weight_lbs: int
    bags_weight_lbs: int
    requires_oxygen: bool
    mobility_equipment: MobilityEquipment
    mobility_notes: str | None


class MissionCreate(BaseModel):
    title: str
    origin_airport: str
    destination_airport: str
    earliest_departure: datetime
    latest_departure: datetime
    estimated_duration_h: float
    coordinator_notes: str | None = None
    required_aircraft_type: list[str] = []
    min_range_nm: int | None = None
    passengers: list[MissionPassengerCreate] = []


class MissionUpdate(BaseModel):
    title: str | None = None
    origin_airport: str | None = None
    destination_airport: str | None = None
    earliest_departure: datetime | None = None
    latest_departure: datetime | None = None
    estimated_duration_h: float | None = None
    status: MissionStatus | None = None
    coordinator_notes: str | None = None
    required_aircraft_type: list[str] | None = None
    min_range_nm: int | None = None


class MissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    origin_airport: str
    destination_airport: str
    earliest_departure: datetime
    latest_departure: datetime
    estimated_duration_h: float
    status: MissionStatus
    coordinator_notes: str | None
    required_aircraft_type: list[str]
    min_range_nm: int | None
    created_at: datetime
    passengers: list[MissionPassengerRead] = []

    @computed_field
    @property
    def total_passenger_weight_lbs(self) -> int:
        return sum(p.weight_lbs for p in self.passengers)

    @computed_field
    @property
    def total_bag_weight_lbs(self) -> int:
        return sum(p.bags_weight_lbs for p in self.passengers)

    @computed_field
    @property
    def total_payload_lbs(self) -> int:
        return sum(p.weight_lbs + p.bags_weight_lbs for p in self.passengers)

    @computed_field
    @property
    def requires_oxygen(self) -> bool:
        return any(p.requires_oxygen for p in self.passengers)

    @computed_field
    @property
    def has_mobility_equipment(self) -> bool:
        return any(p.mobility_equipment != MobilityEquipment.none for p in self.passengers)

    @computed_field
    @property
    def passenger_count(self) -> int:
        return len(self.passengers)


class MissionListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    origin_airport: str
    destination_airport: str
    earliest_departure: datetime
    latest_departure: datetime
    status: MissionStatus
    created_at: datetime
