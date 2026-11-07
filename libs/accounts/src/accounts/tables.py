"""The accounts tables, for building queries.

The schema itself is created and changed only by the Alembic migrations in
migrations/versions/. Keep the two in step: a change here needs a migration.
"""

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Text, Uuid

# Alembic's record of which migrations have run. It has its own name so other
# packages can keep their own migrations in the same database later.
VERSION_TABLE = "accounts_alembic_version"

metadata = MetaData()

users = Table(
    "users",
    metadata,
    # Used only inside the database: for foreign keys and joins.
    Column("id", Integer, primary_key=True, autoincrement=True),
    # How anything outside the database refers to a user (logs, later URLs
    # and APIs). A UUIDv7, set when the user is created and never changed.
    Column("public_id", Uuid, nullable=False, unique=True),
    Column("username", Text, nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
)

sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", Text, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
)
