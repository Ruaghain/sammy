"""Keeping the registry's own tables up to date.

Sammy has one database, shared by every package; whatever starts Sammy
creates the engine. Each package migrates only its own tables, explicitly,
at startup, before any of its services are created: the registry's migrations
live in migrations/ and record what has run in their own version table.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from sammy.core import migration_connection

MIGRATIONS = Path(__file__).parent / "migrations"


def migrate(engine: Engine) -> None:
    """Applies any of the registry's migrations not yet applied to this database."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    with migration_connection(engine) as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
