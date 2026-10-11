"""Encrypt existing TOTP seeds at rest.

Revision ID: 20261011_0014
Revises: 20261011_0013
Create Date: 2026-10-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.encryption import MFA_SECRET_PREFIX, decrypt_mfa_secret, encrypt_mfa_secret

revision: str = "20261011_0014"
down_revision: Union[str, None] = "20261011_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Fernet ciphertext plus the format marker is longer than a base32 TOTP seed.
    op.alter_column(
        "users",
        "two_factor_secret",
        existing_type=sa.String(length=64),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, two_factor_secret FROM users WHERE two_factor_secret IS NOT NULL")
    ).mappings()
    for row in rows:
        value = row["two_factor_secret"]
        if not value.startswith(MFA_SECRET_PREFIX):
            bind.execute(
                sa.text("UPDATE users SET two_factor_secret = :secret WHERE id = :user_id"),
                {"secret": encrypt_mfa_secret(value), "user_id": row["id"]},
            )


def downgrade() -> None:
    # Downgrade restores legacy plaintext storage; only use during a controlled rollback.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, two_factor_secret FROM users WHERE two_factor_secret IS NOT NULL")
    ).mappings()
    for row in rows:
        value = row["two_factor_secret"]
        if value.startswith(MFA_SECRET_PREFIX):
            bind.execute(
                sa.text("UPDATE users SET two_factor_secret = :secret WHERE id = :user_id"),
                {"secret": decrypt_mfa_secret(value), "user_id": row["id"]},
            )
    op.alter_column(
        "users",
        "two_factor_secret",
        existing_type=sa.String(length=512),
        type_=sa.String(length=64),
        existing_nullable=True,
    )
