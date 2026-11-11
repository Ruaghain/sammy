"""Agents

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("short_name", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agents")
