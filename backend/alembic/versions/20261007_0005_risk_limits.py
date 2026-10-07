"""Add portfolio pre-trade risk limits."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261007_0005"
down_revision: Union[str, None] = "20261007_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("max_order_notional", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_position_quantity", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_daily_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_open_orders", sa.Integer(), nullable=True),
        sa.Column("kill_switch", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id"),
    )


def downgrade() -> None:
    op.drop_table("risk_limits")
