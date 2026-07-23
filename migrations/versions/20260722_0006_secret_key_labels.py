"""Add labels and allow one active key per LMS course.

Revision ID: 20260722_0006
Revises: 20260722_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0006"
down_revision: str | None = "20260722_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("secret_keys")}
    if "label" not in columns:
        op.add_column("secret_keys", sa.Column("label", sa.String(120), nullable=True))
        bind.execute(
            sa.text(
                "UPDATE secret_keys "
                "SET label = 'Ранее созданный ключ #' || CAST(id AS VARCHAR)"
            )
        )
        op.alter_column("secret_keys", "label", nullable=False)

    bind.execute(
        sa.text(
            "UPDATE secret_keys AS old_key SET is_active = false "
            "WHERE old_key.is_active = true AND EXISTS ("
            "SELECT 1 FROM secret_keys AS newer_key "
            "WHERE newer_key.lms_course_id = old_key.lms_course_id "
            "AND newer_key.is_active = true AND newer_key.id > old_key.id)"
        )
    )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("secret_keys")}
    if "uq_secret_keys_one_active_per_course" not in indexes:
        op.create_index(
            "uq_secret_keys_one_active_per_course",
            "secret_keys",
            ["lms_course_id"],
            unique=True,
            postgresql_where=sa.text("is_active"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("secret_keys")}
    if "uq_secret_keys_one_active_per_course" in indexes:
        op.drop_index("uq_secret_keys_one_active_per_course", table_name="secret_keys")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("secret_keys")}
    if "label" in columns:
        op.drop_column("secret_keys", "label")
