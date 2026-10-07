"""Add immutable portfolio cash ledger."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261007_0004"
down_revision: Union[str, None] = "20261007_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cash_ledger_type = postgresql.ENUM(
        "OPENING_BALANCE",
        "DEPOSIT",
        "WITHDRAWAL",
        "TRADE",
        "FEE",
        "ADJUSTMENT",
        name="cashledgertype",
    )
    op.create_table(
        "cash_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", cash_ledger_type, nullable=False),
        sa.Column("amount", sa.Numeric(18, 8), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 8), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("execution_fill_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["execution_fill_id"], ["execution_fills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cash_ledger_portfolio_created_at",
        "cash_ledger_entries",
        ["portfolio_id", "created_at"],
    )
    op.create_index(
        "uq_cash_ledger_idempotency_key",
        "cash_ledger_entries",
        ["idempotency_key"],
        unique=True,
    )

    # Existing portfolio balances become auditable opening balances.
    op.execute(sa.text("""
        INSERT INTO cash_ledger_entries
            (id, portfolio_id, entry_type, amount, balance_after, idempotency_key, created_at)
        SELECT
            gen_random_uuid(),
            id,
            'OPENING_BALANCE',
            cash_balance,
            cash_balance,
            'opening:' || id::text,
            created_at
        FROM portfolios
    """))


def downgrade() -> None:
    op.drop_index("uq_cash_ledger_idempotency_key", table_name="cash_ledger_entries")
    op.drop_index("ix_cash_ledger_portfolio_created_at", table_name="cash_ledger_entries")
    op.drop_table("cash_ledger_entries")
    op.execute("DROP TYPE IF EXISTS cashledgertype")
