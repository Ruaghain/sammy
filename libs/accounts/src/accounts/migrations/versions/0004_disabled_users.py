"""Users can be disabled

Revision ID: 0004
Revises: 0003

Adds users.disabled, false for every existing user.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as users:
        users.add_column(
            sa.Column("disabled", sa.Boolean, nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as users:
        users.drop_column("disabled")
