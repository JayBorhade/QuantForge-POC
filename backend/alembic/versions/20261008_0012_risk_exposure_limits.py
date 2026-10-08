"""Extend portfolio risk limits for exposure controls."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261008_0012"
down_revision: Union[str, None] = "20261008_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risk_limits", sa.Column("max_gross_exposure", sa.Numeric(18, 8), nullable=True))
    op.add_column("risk_limits", sa.Column("max_symbol_exposure", sa.Numeric(18, 8), nullable=True))
    op.add_column("risk_limits", sa.Column("max_strategy_exposure", sa.Numeric(18, 8), nullable=True))
    op.add_column("risk_limits", sa.Column("max_strategy_allocation_pct", sa.Numeric(8, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_limits", "max_strategy_allocation_pct")
    op.drop_column("risk_limits", "max_strategy_exposure")
    op.drop_column("risk_limits", "max_symbol_exposure")
    op.drop_column("risk_limits", "max_gross_exposure")
