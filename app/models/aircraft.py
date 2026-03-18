from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Aircraft(Base):
    __tablename__ = "aircraft"

    id: Mapped[int] = mapped_column(primary_key=True)
    tail_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    make_model: Mapped[str] = mapped_column(String(100), nullable=False)
    aircraft_type: Mapped[str] = mapped_column(String(50), nullable=False)
    range_nm: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_lbs: Mapped[int] = mapped_column(Integer, nullable=False)
    num_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    has_oxygen: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ifr_equipped: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    fiki: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    accessibility_notes: Mapped[str | None] = mapped_column(Text)
    home_airport: Mapped[str] = mapped_column(String(4), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pilot_aircraft: Mapped[list["PilotAircraft"]] = relationship(
        "PilotAircraft", back_populates="aircraft", cascade="all, delete-orphan"
    )


class PilotAircraft(Base):
    __tablename__ = "pilot_aircraft"

    id: Mapped[int] = mapped_column(primary_key=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False)
    aircraft_id: Mapped[int] = mapped_column(ForeignKey("aircraft.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text)

    pilot: Mapped["Pilot"] = relationship("Pilot", back_populates="pilot_aircraft")  # noqa: F821
    aircraft: Mapped["Aircraft"] = relationship("Aircraft", back_populates="pilot_aircraft")
