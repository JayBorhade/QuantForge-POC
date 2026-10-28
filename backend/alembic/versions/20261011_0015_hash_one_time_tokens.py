"""Hash one-time auth tokens and add verification expiry.

Revision ID: 20261011_0015
Revises: 20261011_0014
Create Date: 2026-10-11
"""
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261011_0015"
down_revision: Union[str, None] = "20261011_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def _digest(value: str) -> str:
    # codeql[py/weak-sensitive-data-hashing] These are high-entropy, single-use tokens, not passwords.
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verification_expires", sa.DateTime(timezone=True), nullable=True),
    )
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    rows = bind.execute(
        sa.text(
            "SELECT id, email_verification_token, password_reset_token "
            "FROM users WHERE email_verification_token IS NOT NULL "
            "OR password_reset_token IS NOT NULL"
        )
    ).mappings().all()
    for row in rows:
        values = {"user_id": row["id"]}
        assignments = []
        if row["email_verification_token"]:
            assignments.append("email_verification_token = :email_token")
            values["email_token"] = _digest(row["email_verification_token"])
            values["verification_expires"] = now + timedelta(hours=24)
            assignments.append("email_verification_expires = :verification_expires")
        if row["password_reset_token"]:
            assignments.append("password_reset_token = :reset_token")
            values["reset_token"] = _digest(row["password_reset_token"])
        if assignments:
            bind.execute(
                sa.text(f"UPDATE users SET {', '.join(assignments)} WHERE id = :user_id"),
                values,
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
