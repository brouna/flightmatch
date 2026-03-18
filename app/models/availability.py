from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Enum, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class AvailabilitySource(str, enum.Enum):
    manual = "manual"
    google = "google"
    apple = "apple"
    outlook = "outlook"


class CalendarProvider(str, enum.Enum):
    google = "google"
    outlook = "outlook"
    apple = "apple"


class PilotAvailability(Base):
    __tablename__ = "pilot_availability"
    __table_args__ = (
        Index("ix_pilot_availability_pilot_time", "pilot_id", "start_time", "end_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[AvailabilitySource] = mapped_column(Enum(AvailabilitySource), nullable=False)
    is_busy: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    calendar_uid: Mapped[str | None] = mapped_column(String(500), index=True)

    pilot: Mapped["Pilot"] = relationship("Pilot", back_populates="availability")  # noqa: F821


class CalendarIntegration(Base):
    __tablename__ = "calendar_integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[CalendarProvider] = mapped_column(Enum(CalendarProvider), nullable=False)
    access_token: Mapped[str | None] = mapped_column(String(2000))   # stored encrypted
    refresh_token: Mapped[str | None] = mapped_column(String(2000))  # stored encrypted
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calendar_id: Mapped[str | None] = mapped_column(String(500))
    caldav_url: Mapped[str | None] = mapped_column(String(500))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pilot: Mapped["Pilot"] = relationship("Pilot", back_populates="calendar_integrations")  # noqa: F821
