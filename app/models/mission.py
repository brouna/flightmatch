from datetime import datetime
from sqlalchemy import String, Float, ForeignKey, Text, DateTime, Integer, ARRAY, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class MissionStatus(str, enum.Enum):
    open = "open"
    matched = "matched"
    completed = "completed"
    cancelled = "cancelled"


class MobilityEquipment(str, enum.Enum):
    none = "none"
    wheelchair = "wheelchair"
    walker = "walker"
    other = "other"


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_airport: Mapped[str] = mapped_column(String(4), nullable=False)
    destination_airport: Mapped[str] = mapped_column(String(4), nullable=False)
    earliest_departure: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_departure: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_duration_h: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[MissionStatus] = mapped_column(
        String(20), default=MissionStatus.open, server_default="open"
    )
    coordinator_notes: Mapped[str | None] = mapped_column(Text)
    required_aircraft_type: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    min_range_nm: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    passengers: Mapped[list["MissionPassenger"]] = relationship(
        "MissionPassenger", back_populates="mission", cascade="all, delete-orphan"
    )
    match_logs: Mapped[list["MatchLog"]] = relationship(  # noqa: F821
        "MatchLog", back_populates="mission"
    )


class MissionPassenger(Base):
    __tablename__ = "mission_passengers"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    weight_lbs: Mapped[int] = mapped_column(Integer, nullable=False)
    bags_weight_lbs: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    requires_oxygen: Mapped[bool] = mapped_column(default=False, server_default="false")
    mobility_equipment: Mapped[MobilityEquipment] = mapped_column(
        String(20), default=MobilityEquipment.none, server_default="none"
    )
    mobility_notes: Mapped[str | None] = mapped_column(Text)

    mission: Mapped["Mission"] = relationship("Mission", back_populates="passengers")
