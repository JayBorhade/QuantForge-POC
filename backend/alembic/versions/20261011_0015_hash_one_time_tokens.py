"""Hash one-time auth tokens and add verification expiry.

Revision ID: 20261011_0015
Revises: 20261011_0014
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261011_0015"
down_revision: Union[str, None] = "20261011_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verification_expires", sa.DateTime(timezone=True), nullable=True),
    )
    bind = op.get_bind()
    # Legacy plaintext tokens cannot be safely converted to keyed digests without
    # retaining their raw values in application code. Invalidate them on upgrade.
    bind.execute(
        sa.text(
            "UPDATE users SET email_verification_token = NULL, password_reset_token = NULL "
            "WHERE email_verification_token IS NOT NULL OR password_reset_token IS NOT NULL"
        )
    )


def downgrade() -> None:
    # Digests cannot be reversed. Existing one-time tokens are invalidated rather
    # than restoring plaintext token material to the database.
    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE users SET email_verification_token = NULL, "
        "email_verification_expires = NULL, password_reset_token = NULL"
    ))
    op.drop_column("users", "email_verification_expires")
