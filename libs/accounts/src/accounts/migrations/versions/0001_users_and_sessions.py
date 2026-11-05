"""Users and sessions

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
        "users",
        sa.Column("username", sa.Text, primary_key=True),
        sa.Column("password_hash", sa.Text, nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.Text, primary_key=True),
        sa.Column("username", sa.Text, sa.ForeignKey("users.username"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("users")
