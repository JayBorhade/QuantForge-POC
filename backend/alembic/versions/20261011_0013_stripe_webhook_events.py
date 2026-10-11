"""Persist Stripe webhook idempotency keys."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261011_0013"
down_revision: Union[str, None] = "20261008_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stripe_webhook_events",
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
