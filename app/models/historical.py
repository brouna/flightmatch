from datetime import date, datetime
from sqlalchemy import String, Boolean, Float, ForeignKey, Date, DateTime, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class FlightType(str, enum.Enum):
    private = "private"
    commercial = "commercial"


class FlightSource(str, enum.Enum):
    imported = "import"
    logged = "logged"


class HistoricalFlight(Base):
    __tablename__ = "historical_flights"

    id: Mapped[int] = mapped_column(primary_key=True)
    pilot_id: Mapped[int | None] = mapped_column(ForeignKey("pilots.id", ondelete="SET NULL"))
    aircraft_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin_airport: Mapped[str] = mapped_column(String(4), nullable=False)
    destination_airport: Mapped[str] = mapped_column(String(4), nullable=False)
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)
    distance_nm: Mapped[float | None] = mapped_column(Float)
    duration_h: Mapped[float | None] = mapped_column(Float)
    num_passengers: Mapped[int | None] = mapped_column(Integer)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    flight_type: Mapped[FlightType | None] = mapped_column(String(20))
    source: Mapped[FlightSource] = mapped_column(
        String(20), default=FlightSource.logged, server_default="logged"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pilot: Mapped["Pilot | None"] = relationship("Pilot", back_populates="historical_flights")  # noqa: F821
