"""Store native Telegram poll bindings.

Revision ID: 20260721_0003
Revises: 20260720_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0003"
down_revision: str | None = "20260720_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "telegram_polls" not in inspector.get_table_names():
        op.create_table(
            "telegram_polls",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("telegram_poll_id", sa.String(length=255), nullable=False),
            sa.Column("practice_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["practice_id"], ["practices.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("telegram_poll_id"),
        )
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("telegram_polls")}
    index_name = op.f("ix_telegram_polls_telegram_poll_id")
    if index_name not in indexes:
        op.create_index(index_name, "telegram_polls", ["telegram_poll_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "telegram_polls" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("telegram_polls")}
        index_name = op.f("ix_telegram_polls_telegram_poll_id")
        if index_name in indexes:
            op.drop_index(index_name, table_name="telegram_polls")
        op.drop_table("telegram_polls")
