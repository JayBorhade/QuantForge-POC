"""Add durable worker lease identity and enforce backtest run uniqueness."""
from alembic import op
import sqlalchemy as sa

revision = "20261008_0009"
down_revision = "20261008_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("strategy_runs", sa.Column("worker_token", sa.String(length=64), nullable=True))
    op.add_column("strategy_runs", sa.Column("identity_key", sa.String(length=128), nullable=True))
    op.add_column("strategy_runs", sa.Column("worker_started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_strategy_runs_worker_token", "strategy_runs", ["worker_token"])
    op.create_index("ix_strategy_runs_identity_key", "strategy_runs", ["identity_key"])
    # Keep the newest replayable run when legacy rows contain duplicate identities.
    op.execute(sa.text("""
        UPDATE strategy_runs
        SET identity_key = strategy_id::text || ':' || mode::text || ':' || configuration_fingerprint
        WHERE configuration_fingerprint IS NOT NULL
          AND status::text NOT IN ('failed', 'cancelled')
    """))
    op.execute(sa.text("""
        DELETE FROM strategy_runs
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY identity_key
                           ORDER BY created_at DESC, id DESC
                       ) AS duplicate_rank
                FROM strategy_runs
                WHERE identity_key IS NOT NULL
            ) ranked
            WHERE duplicate_rank > 1
        )
    """))
    op.create_index(
        "uq_strategy_runs_backtest_identity",
        "strategy_runs",
        ["strategy_id", "mode", "identity_key"],
        unique=True,
        postgresql_where=sa.text("identity_key IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_strategy_runs_backtest_identity", table_name="strategy_runs")
    op.drop_index("ix_strategy_runs_identity_key", table_name="strategy_runs")
    op.drop_index("ix_strategy_runs_worker_token", table_name="strategy_runs")
    op.drop_column("strategy_runs", "identity_key")
    op.drop_column("strategy_runs", "worker_started_at")
    op.drop_column("strategy_runs", "worker_token")
