from datetime import date, datetime
from sqlalchemy import String, Boolean, Float, ForeignKey, Date, DateTime, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class FlightOutcome(str, enum.Enum):
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class FlightSource(str, enum.Enum):
    imported = "import"
    logged = "logged"


class HistoricalFlight(Base):
    __tablename__ = "historical_flights"

    id: Mapped[int] = mapped_column(primary_key=True)
    pilot_id: Mapped[int | None] = mapped_column(ForeignKey("pilots.id", ondelete="SET NULL"))
    aircraft_type: Mapped[str] = mapped_column(String(50), nullable=False)
    origin_airport: Mapped[str] = mapped_column(String(4), nullable=False)
    destination_airport: Mapped[str] = mapped_column(String(4), nullable=False)
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)
    distance_nm: Mapped[float | None] = mapped_column(Float)
    duration_h: Mapped[float | None] = mapped_column(Float)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    outcome: Mapped[FlightOutcome | None] = mapped_column(Enum(FlightOutcome))
    source: Mapped[FlightSource] = mapped_column(
        Enum(FlightSource), default=FlightSource.logged, server_default="logged"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pilot: Mapped["Pilot | None"] = relationship("Pilot", back_populates="historical_flights")  # noqa: F821
