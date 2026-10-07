"""backfill IDs for existing students

Revision ID: 20261002backfill
Revises: 20261002studentid
Create Date: 2026-10-02
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261002backfill"
down_revision: Union[str, Sequence[str], None] = "20261002studentid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE users "
        "SET student_id = 'EH-' || LPAD(id::text, 6, '0') "
        "WHERE role = 'STUDENT' AND student_id IS NULL"
    )


def downgrade() -> None:
    pass