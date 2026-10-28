"""Prevent replay of TOTP time steps.

Revision ID: 20261011_0016
Revises: 20261011_0015
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261011_0016"
down_revision: Union[str, None] = "20261011_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_totp_step", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_totp_step")
