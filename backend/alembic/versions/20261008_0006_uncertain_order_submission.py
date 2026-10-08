"""Add an explicit state for uncertain broker submissions."""

from typing import Sequence, Union

from alembic import op

revision: str = "20261008_0006"
down_revision: Union[str, None] = "20261007_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'SUBMISSION_UNKNOWN'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place. The state remains
    # part of the enum for downgrade compatibility with any persisted records.
    pass
