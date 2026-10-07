"""add student ID to users

Revision ID: 20261002studentid
Revises: 20260930absent
Create Date: 2026-10-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261002studentid"
down_revision: Union[str, Sequence[str], None] = "20260930absent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("student_id", sa.String(length=30), nullable=True))
    op.create_index("ix_users_student_id", "users", ["student_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_student_id", table_name="users")
    op.drop_column("users", "student_id")