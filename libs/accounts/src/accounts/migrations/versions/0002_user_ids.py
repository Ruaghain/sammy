"""Give users an internal id and a public id

Revision ID: 0002
Revises: 0001

users gains an auto-incrementing id (the new primary key) and a UUIDv7
public_id; sessions refer to users by id instead of username. SQLite can't
change a primary key in place, so both tables are rebuilt: the old ones are
renamed aside, new ones created, the data copied across, and the old ones
dropped. The new primary keys are named explicitly because on PostgreSQL the
renamed tables still hold the default names (users_pkey, sessions_pkey).
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("sessions", "sessions_0001")
    op.rename_table("users", "users_0001")

    users = op.create_table(
        "users",
        sa.Column("id", sa.Integer, autoincrement=True),
        sa.Column("public_id", sa.Uuid, nullable=False, unique=True),
        sa.Column("username", sa.Text, nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    sessions = op.create_table(
        "sessions",
        sa.Column("token_hash", sa.Text),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.PrimaryKeyConstraint("token_hash", name="pk_sessions"),
    )

    database = op.get_bind()
    old_users = sa.table("users_0001", sa.column("username"), sa.column("password_hash"))
    for username, password_hash in database.execute(sa.select(old_users)).all():
        database.execute(
            sa.insert(users).values(
                public_id=uuid.uuid7(), username=username, password_hash=password_hash
            )
        )

    old_sessions = sa.table("sessions_0001", sa.column("token_hash"), sa.column("username"))
    database.execute(
        sa.insert(sessions).from_select(
            ["token_hash", "user_id"],
            sa.select(old_sessions.c.token_hash, users.c.id).join(
                users, users.c.username == old_sessions.c.username
            ),
        )
    )

    op.drop_table("sessions_0001")
    op.drop_table("users_0001")


def downgrade() -> None:
    op.rename_table("sessions", "sessions_0002")
    op.rename_table("users", "users_0002")

    users = op.create_table(
        "users",
        sa.Column("username", sa.Text, primary_key=True),
        sa.Column("password_hash", sa.Text, nullable=False),
    )
    sessions = op.create_table(
        "sessions",
        sa.Column("token_hash", sa.Text, primary_key=True),
        sa.Column("username", sa.Text, sa.ForeignKey("users.username"), nullable=False),
    )

    new_users = sa.table(
        "users_0002", sa.column("id"), sa.column("username"), sa.column("password_hash")
    )
    new_sessions = sa.table("sessions_0002", sa.column("token_hash"), sa.column("user_id"))
    database = op.get_bind()
    database.execute(
        sa.insert(users).from_select(
            ["username", "password_hash"],
            sa.select(new_users.c.username, new_users.c.password_hash),
        )
    )
    database.execute(
        sa.insert(sessions).from_select(
            ["token_hash", "username"],
            sa.select(new_sessions.c.token_hash, new_users.c.username).join(
                new_users, new_users.c.id == new_sessions.c.user_id
            ),
        )
    )

    op.drop_table("sessions_0002")
    op.drop_table("users_0002")
