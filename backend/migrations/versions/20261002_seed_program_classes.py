"""seed student program classes

Revision ID: 20261002classes
Revises: 20261002backfill
Create Date: 2026-10-02
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261002classes"
down_revision: Union[str, Sequence[str], None] = "20261002backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO classes (name, status) VALUES "
        "('IT class', 'ACTIVE'), ('Hair & Beauty', 'ACTIVE'), ('Catering', 'ACTIVE') "
        "ON CONFLICT (name) DO NOTHING"
    )


def downgrade() -> None:
    pass