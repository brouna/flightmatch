"""Make historical_flights.aircraft_type nullable

Revision ID: 004
Revises: 003
Create Date: 2026-03-19

"""
from typing import Sequence, Union
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("historical_flights", "aircraft_type", nullable=True)


def downgrade() -> None:
    op.alter_column("historical_flights", "aircraft_type", nullable=False)
