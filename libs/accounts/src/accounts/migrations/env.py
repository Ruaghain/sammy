"""Alembic environment for the accounts schema.

Sammy runs these migrations itself at startup (accounts.migrate), passing in an open
connection. Run by hand (e.g. to create a new revision), it connects to
SAMMY_DATABASE_URL instead.
"""

import os

from alembic import context
from sqlalchemy import create_engine

from accounts.tables import VERSION_TABLE, metadata


def run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=metadata,
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    run_migrations(connection)
else:
    engine = create_engine(os.environ["SAMMY_DATABASE_URL"])
    with engine.begin() as connection:
        run_migrations(connection)
