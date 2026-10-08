"""Add production paper-strategy scheduler state and portfolio binding."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261008_0010"
down_revision = "20261008_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "strategies",
        sa.Column("schedule_portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "strategies",
        sa.Column("last_scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_strategies_schedule_portfolio_id",
        "strategies",
        "portfolios",
        ["schedule_portfolio_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_strategies_schedule_portfolio_id",
        "strategies",
        ["schedule_portfolio_id"],
    )
    op.create_index(
        "ix_strategies_last_scheduled_at",
        "strategies",
        ["last_scheduled_at"],
    )


def downgrade():
    op.drop_index("ix_strategies_last_scheduled_at", table_name="strategies")
    op.drop_index("ix_strategies_schedule_portfolio_id", table_name="strategies")
    op.drop_constraint(
        "fk_strategies_schedule_portfolio_id",
        "strategies",
        type_="foreignkey",
    )
    op.drop_column("strategies", "last_scheduled_at")
    op.drop_column("strategies", "schedule_portfolio_id")
