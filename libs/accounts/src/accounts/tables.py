"""The accounts tables, for building queries.

The schema itself is created and changed only by the Alembic migrations in
migrations/versions/. Keep the two in step: a change here needs a migration.
"""

from sqlalchemy import Column, ForeignKey, MetaData, Table, Text

# Alembic's record of which migrations have run. It has its own name so other
# packages can keep their own migrations in the same database later.
VERSION_TABLE = "accounts_alembic_version"

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("username", Text, primary_key=True),
    Column("password_hash", Text, nullable=False),
)

sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", Text, primary_key=True),
    Column("username", Text, ForeignKey("users.username"), nullable=False),
)
