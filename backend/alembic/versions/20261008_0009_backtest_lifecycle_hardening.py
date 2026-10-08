"""Add durable worker lease identity and enforce backtest run uniqueness."""
from alembic import op
import sqlalchemy as sa

revision = "20261008_0009_backtest_lifecycle_hardening"
down_revision = "20261008_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("strategy_runs", sa.Column("worker_token", sa.String(length=64), nullable=True))
    op.add_column("strategy_runs", sa.Column("worker_started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_strategy_runs_worker_token", "strategy_runs", ["worker_token"])
    # Keep the newest replayable run when legacy rows contain duplicate identities.
    op.execute(sa.text("""
        DELETE FROM strategy_runs
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY strategy_id, mode, configuration_fingerprint
                           ORDER BY created_at DESC, id DESC
                       ) AS duplicate_rank
                FROM strategy_runs
                WHERE configuration_fingerprint IS NOT NULL
            ) ranked
            WHERE duplicate_rank > 1
        )
    """))
    op.create_index(
        "uq_strategy_runs_backtest_identity",
        "strategy_runs",
        ["strategy_id", "mode", "configuration_fingerprint"],
        unique=True,
        postgresql_where=sa.text("configuration_fingerprint IS NOT NULL AND status NOT IN ('failed', 'cancelled')"),
    )


def downgrade():
    op.drop_index("uq_strategy_runs_backtest_identity", table_name="strategy_runs")
    op.drop_index("ix_strategy_runs_worker_token", table_name="strategy_runs")
    op.drop_column("strategy_runs", "worker_started_at")
    op.drop_column("strategy_runs", "worker_token")
