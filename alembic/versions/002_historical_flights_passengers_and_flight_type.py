"""Add num_passengers and replace outcome with flight_type on historical_flights

Revision ID: 002
Revises: 001
Create Date: 2026-03-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("historical_flights", sa.Column("num_passengers", sa.Integer()))
    op.add_column("historical_flights", sa.Column("flight_type", sa.String(20)))
    op.drop_column("historical_flights", "outcome")


def downgrade() -> None:
    op.add_column("historical_flights", sa.Column("outcome", sa.String(20)))
    op.drop_column("historical_flights", "flight_type")
    op.drop_column("historical_flights", "num_passengers")
