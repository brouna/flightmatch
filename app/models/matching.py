from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Enum, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class PilotResponse(str, enum.Enum):
    accepted = "accepted"
    declined = "declined"
    no_response = "no_response"


class MatchingRule(Base):
    __tablename__ = "matching_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rule_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MatchLog(Base):
    __tablename__ = "match_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    pilot_id: Mapped[int] = mapped_column(ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    hard_filter_pass: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    score: Mapped[float | None] = mapped_column(Numeric(6, 4))
    rank: Mapped[int | None] = mapped_column()
    features_json: Mapped[dict | None] = mapped_column(JSONB)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    pilot_response: Mapped[PilotResponse] = mapped_column(
        Enum(PilotResponse), default=PilotResponse.no_response, server_default="no_response"
    )
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    mission: Mapped["Mission"] = relationship("Mission", back_populates="match_logs")  # noqa: F821
    pilot: Mapped["Pilot"] = relationship("Pilot", back_populates="match_logs")  # noqa: F821
