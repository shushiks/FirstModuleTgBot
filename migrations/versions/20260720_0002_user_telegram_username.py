"""Add searchable Telegram username to users.

Revision ID: 20260720_0002
Revises: 20260718_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260720_0002"
down_revision: str | None = "20260718_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "telegram_username" not in columns:
        op.add_column(
            "users",
            sa.Column("telegram_username", sa.String(length=32), nullable=True),
        )

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    index_name = op.f("ix_users_telegram_username")
    if index_name not in indexes:
        op.create_index(
            index_name,
            "users",
            ["telegram_username"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    index_name = op.f("ix_users_telegram_username")
    if index_name in indexes:
        op.drop_index(index_name, table_name="users")

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "telegram_username" in columns:
        op.drop_column("users", "telegram_username")
