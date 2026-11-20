"""Add hashed MFA recovery-code storage.

Revision ID: 20261011_0017
Revises: 20261011_0016
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261011_0017"
down_revision: Union[str, None] = "20261011_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("two_factor_recovery_codes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "two_factor_recovery_codes")
