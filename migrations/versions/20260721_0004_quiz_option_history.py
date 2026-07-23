"""Keep historical quiz options when a practice is edited.

Revision ID: 20260721_0004
Revises: 20260721_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0004"
down_revision: str | None = "20260721_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("quiz_options")}
    if "is_active" not in columns:
        op.add_column(
            "quiz_options",
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("quiz_options")}
    if "is_active" in columns:
        op.drop_column("quiz_options", "is_active")
