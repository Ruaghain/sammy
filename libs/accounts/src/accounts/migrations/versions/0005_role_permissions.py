"""What each role allows

Revision ID: 0005
Revises: 0004

Adds role_permissions: one row per permission a role grants. The built-in
admin role needs none, because it has every permission by definition.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission", sa.Text, primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("role_permissions")
