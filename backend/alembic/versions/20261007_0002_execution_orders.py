"""Add execution order tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261007_0002"
down_revision: Union[str, None] = "20261007_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    order_side = postgresql.ENUM("BUY", "SELL", name="orderside")
    order_type = postgresql.ENUM("MARKET", "LIMIT", name="ordertype")
    order_status = postgresql.ENUM("PENDING", "SUBMITTED", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED", "FAILED", name="orderstatus")
    execution_mode = postgresql.ENUM("PAPER", "LIVE", name="executionmode")

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_order_id", sa.String(length=64), nullable=False),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", order_side, nullable=False),
        sa.Column("order_type", order_type, nullable=False),
        sa.Column("mode", execution_mode, nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("limit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("filled_quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("average_fill_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("status", order_status, nullable=False),
        sa.Column("rejection_reason", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_orders_portfolio_client_order_id", "orders", ["portfolio_id", "client_order_id"], unique=True)
    op.create_index("ix_orders_broker_order_id", "orders", ["broker_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_broker_order_id", table_name="orders")
    op.drop_index("uq_orders_portfolio_client_order_id", table_name="orders")
    op.drop_table("orders")
    bind = op.get_bind()
    for name in ("executionmode", "orderstatus", "ordertype", "orderside"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
