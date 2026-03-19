"""Make pilot email and home_airport optional

Revision ID: 003
Revises: 002
Create Date: 2026-03-19

"""
from typing import Sequence, Union
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("pilots", "email", nullable=True)
    op.alter_column("pilots", "home_airport", nullable=True)


def downgrade() -> None:
    op.alter_column("pilots", "home_airport", nullable=False)
    op.alter_column("pilots", "email", nullable=False)
