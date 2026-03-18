"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pilots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("home_airport", sa.String(4), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("certifications", ARRAY(sa.String), server_default="{}"),
        sa.Column("preferred_regions", ARRAY(sa.String), server_default="{}"),
        sa.Column("max_range_nm", sa.Integer),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_pilots_email", "pilots", ["email"])

    op.create_table(
        "aircraft",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tail_number", sa.String(10), unique=True, nullable=False),
        sa.Column("make_model", sa.String(100), nullable=False),
        sa.Column("aircraft_type", sa.String(50), nullable=False),
        sa.Column("range_nm", sa.Integer, nullable=False),
        sa.Column("payload_lbs", sa.Integer, nullable=False),
        sa.Column("num_seats", sa.Integer, nullable=False),
        sa.Column("has_oxygen", sa.Boolean, server_default="false"),
        sa.Column("ifr_equipped", sa.Boolean, server_default="true"),
        sa.Column("fiki", sa.Boolean, server_default="false"),
        sa.Column("is_accessible", sa.Boolean, server_default="false"),
        sa.Column("accessibility_notes", sa.Text),
        sa.Column("home_airport", sa.String(4), nullable=False),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "pilot_aircraft",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pilot_id", sa.Integer, sa.ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("aircraft_id", sa.Integer, sa.ForeignKey("aircraft.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "missions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("origin_airport", sa.String(4), nullable=False),
        sa.Column("destination_airport", sa.String(4), nullable=False),
        sa.Column("earliest_departure", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_departure", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_duration_h", sa.Float, nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("coordinator_notes", sa.Text),
        sa.Column("required_aircraft_type", ARRAY(sa.String), server_default="{}"),
        sa.Column("min_range_nm", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "mission_passengers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_lbs", sa.Integer, nullable=False),
        sa.Column("bags_weight_lbs", sa.Integer, server_default="0"),
        sa.Column("requires_oxygen", sa.Boolean, server_default="false"),
        sa.Column("mobility_equipment", sa.String(20), server_default="none"),
        sa.Column("mobility_notes", sa.Text),
    )

    op.create_table(
        "pilot_availability",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pilot_id", sa.Integer, sa.ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("is_busy", sa.Boolean, server_default="true"),
        sa.Column("calendar_uid", sa.String(500)),
    )
    op.create_index(
        "ix_pilot_availability_pilot_time",
        "pilot_availability",
        ["pilot_id", "start_time", "end_time"],
    )
    op.create_index("ix_pilot_availability_uid", "pilot_availability", ["calendar_uid"])

    op.create_table(
        "calendar_integrations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pilot_id", sa.Integer, sa.ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("access_token", sa.String(2000)),
        sa.Column("refresh_token", sa.String(2000)),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("calendar_id", sa.String(500)),
        sa.Column("caldav_url", sa.String(500)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("sync_enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "historical_flights",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pilot_id", sa.Integer, sa.ForeignKey("pilots.id", ondelete="SET NULL")),
        sa.Column("aircraft_type", sa.String(50), nullable=False),
        sa.Column("origin_airport", sa.String(4), nullable=False),
        sa.Column("destination_airport", sa.String(4), nullable=False),
        sa.Column("flight_date", sa.Date, nullable=False),
        sa.Column("distance_nm", sa.Float),
        sa.Column("duration_h", sa.Float),
        sa.Column("accepted", sa.Boolean, server_default="true"),
        sa.Column("outcome", sa.String(20)),
        sa.Column("source", sa.String(20), server_default="logged"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "matching_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("rule_key", sa.String(50), unique=True, nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("parameters", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "match_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pilot_id", sa.Integer, sa.ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("hard_filter_pass", sa.Boolean, server_default="true"),
        sa.Column("score", sa.Numeric(6, 4)),
        sa.Column("rank", sa.Integer),
        sa.Column("features_json", JSONB),
        sa.Column("notification_sent", sa.Boolean, server_default="false"),
        sa.Column("pilot_response", sa.String(20), server_default="no_response"),
        sa.Column("response_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("match_logs")
    op.drop_table("matching_rules")
    op.drop_table("historical_flights")
    op.drop_table("calendar_integrations")
    op.drop_table("pilot_availability")
    op.drop_table("mission_passengers")
    op.drop_table("missions")
    op.drop_table("pilot_aircraft")
    op.drop_table("aircraft")
    op.drop_table("pilots")
