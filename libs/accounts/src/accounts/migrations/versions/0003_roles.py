"""Roles, and which users hold them

Revision ID: 0003
Revises: 0002

Adds roles and user_roles, and creates the built-in admin role.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    roles = op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), primary_key=True),
    )
    op.bulk_insert(roles, [{"name": "admin"}])


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("roles")
