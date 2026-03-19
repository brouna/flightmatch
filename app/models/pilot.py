from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ARRAY, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Pilot(Base):
    __tablename__ = "pilots"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    home_airport: Mapped[str | None] = mapped_column(String(4), nullable=True)  # ICAO
    phone: Mapped[str | None] = mapped_column(String(20))
    certifications: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    preferred_regions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    max_range_nm: Mapped[int | None] = mapped_column()
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    pilot_aircraft: Mapped[list["PilotAircraft"]] = relationship(  # noqa: F821
        "PilotAircraft", back_populates="pilot", cascade="all, delete-orphan"
    )
    availability: Mapped[list["PilotAvailability"]] = relationship(  # noqa: F821
        "PilotAvailability", back_populates="pilot", cascade="all, delete-orphan"
    )
    calendar_integrations: Mapped[list["CalendarIntegration"]] = relationship(  # noqa: F821
        "CalendarIntegration", back_populates="pilot", cascade="all, delete-orphan"
    )
    historical_flights: Mapped[list["HistoricalFlight"]] = relationship(  # noqa: F821
        "HistoricalFlight", back_populates="pilot"
    )
    match_logs: Mapped[list["MatchLog"]] = relationship(  # noqa: F821
        "MatchLog", back_populates="pilot"
    )
