"""The registry's tables, for building queries.

The schema itself is created and changed only by the Alembic migrations in
migrations/versions/. Keep the two in step: a change here needs a migration.
"""

from sqlalchemy import Column, Integer, MetaData, Table, Text

# Alembic's record of which of the registry's migrations have run, kept apart
# from other packages' in the same database.
VERSION_TABLE = "registry_alembic_version"

metadata = MetaData()

agents = Table(
    "agents",
    metadata,
    # Used only inside the database.
    Column("id", Integer, primary_key=True, autoincrement=True),
    # How everything outside the registry refers to the agent (permissions,
    # its model setting, logs). Chosen when it's added and never changed.
    Column("short_name", Text, nullable=False, unique=True),
    # Shown to people; can be changed.
    Column("name", Text, nullable=False, unique=True),
    # What the orchestrator's model chooses agents by; can be changed.
    Column("description", Text, nullable=False),
)
