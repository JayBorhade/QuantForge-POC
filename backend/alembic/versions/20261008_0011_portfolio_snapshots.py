"""Add historical portfolio equity snapshots."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261008_0011"
down_revision = "20261008_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", sa.Numeric(18, 4), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("position_market_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(18, 4), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_pnl", sa.Numeric(18, 4), nullable=False),
        sa.Column("daily_return", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("drawdown", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_portfolio_snapshots_portfolio_recorded_at",
        "portfolio_snapshots",
        ["portfolio_id", "recorded_at"],
    )


def downgrade():
    op.drop_index("ix_portfolio_snapshots_portfolio_recorded_at", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
