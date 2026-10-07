"""add social login subject IDs to students

Revision ID: 20261002oauthids
Revises: 20261002classes
Create Date: 2026-10-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261002oauthids"
down_revision: Union[str, Sequence[str], None] = "20261002classes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("apple_subject", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_google_subject", "users", ["google_subject"])
    op.create_unique_constraint("uq_users_apple_subject", "users", ["apple_subject"])


def downgrade() -> None:
    op.drop_constraint("uq_users_apple_subject", "users", type_="unique")
    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.drop_column("users", "apple_subject")
    op.drop_column("users", "google_subject")