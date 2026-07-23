"""Store LMS keys as keyed digests instead of plaintext.

Revision ID: 20260722_0005
Revises: 20260721_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from zero_semester.services.secrets import digest_secret

revision: str = "20260722_0005"
down_revision: str | None = "20260721_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("secret_keys")}
    if "key_digest" not in columns:
        op.add_column("secret_keys", sa.Column("key_digest", sa.String(64), nullable=True))
        rows = bind.execute(sa.text("SELECT id, normalized_value FROM secret_keys")).all()
        for key_id, plaintext in rows:
            bind.execute(
                sa.text("UPDATE secret_keys SET key_digest = :digest WHERE id = :id"),
                {"digest": digest_secret(plaintext), "id": key_id},
            )
        op.alter_column("secret_keys", "key_digest", nullable=False)
        op.create_unique_constraint(
            "uq_secret_keys_key_digest",
            "secret_keys",
            ["key_digest"],
        )
    if "normalized_value" in columns:
        op.drop_constraint("uq_secret_keys_normalized_value", "secret_keys", type_="unique")
        op.drop_column("secret_keys", "normalized_value")


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("secret_keys")}
    if "normalized_value" not in columns:
        op.add_column("secret_keys", sa.Column("normalized_value", sa.String(255), nullable=True))
    if "key_digest" in columns:
        op.drop_constraint("uq_secret_keys_key_digest", "secret_keys", type_="unique")
        op.drop_column("secret_keys", "key_digest")
