"""Persist immutable inputs required to replay backtest runs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261008_0008"
down_revision = "20261008_0007"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("strategy_runs", sa.Column("initial_capital", sa.Numeric(18, 4), nullable=True))
    op.add_column("strategy_runs", sa.Column("input_snapshot", postgresql.JSONB(), nullable=True))

def downgrade():
    op.drop_column("strategy_runs", "input_snapshot")
    op.drop_column("strategy_runs", "initial_capital")
