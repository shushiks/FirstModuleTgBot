"""Initial application schema.

Revision ID: 20260718_0001
Revises:
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import insert

from zero_semester.models import Base, School
from zero_semester.models.enums import SchoolCode

revision: str = "20260718_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    bind.execute(
        insert(School),
        [
            {"code": SchoolCode.TECHNOLOGY, "name": "Школа технологий"},
            {"code": SchoolCode.DESIGN, "name": "Школа дизайна"},
        ],
    )


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
