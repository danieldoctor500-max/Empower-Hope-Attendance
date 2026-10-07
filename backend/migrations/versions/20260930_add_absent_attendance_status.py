"""add absent attendance status

Revision ID: 20260930absent
Revises: 50cdb847000f
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260930absent"
down_revision: Union[str, Sequence[str], None] = "50cdb847000f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE attendance_status ADD VALUE IF NOT EXISTS 'ABSENT' BEFORE 'INCOMPLETE'")


def downgrade() -> None:
    pass