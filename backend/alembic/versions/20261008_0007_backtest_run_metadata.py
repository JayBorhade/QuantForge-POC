"""Persist reproducibility metadata for strategy runs."""
from alembic import op
import sqlalchemy as sa
revision="20261008_0007"; down_revision="20261008_0006"; branch_labels=None; depends_on=None
def upgrade():
    op.add_column("strategy_runs",sa.Column("configuration_fingerprint",sa.String(length=64),nullable=True))
    op.add_column("strategy_runs",sa.Column("data_source",sa.String(length=128),nullable=True))
    op.add_column("strategy_runs",sa.Column("data_revision",sa.String(length=128),nullable=True))
    op.create_index("ix_strategy_runs_configuration_fingerprint","strategy_runs",["configuration_fingerprint"])
def downgrade():
    op.drop_index("ix_strategy_runs_configuration_fingerprint",table_name="strategy_runs")
    op.drop_column("strategy_runs","data_revision"); op.drop_column("strategy_runs","data_source"); op.drop_column("strategy_runs","configuration_fingerprint")
