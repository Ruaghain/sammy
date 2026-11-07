"""Connecting to Sammy's database and keeping its schema up to date."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine

MIGRATIONS = Path(__file__).parent / "migrations"


def connect(database_url: str) -> Engine:
    """An engine for this SQLAlchemy URL (sqlite:///path/to/sammy.sqlite or
    postgresql+psycopg://user:password@host/database), with the schema brought
    up to date by applying any migrations not yet applied."""
    engine = create_engine(database_url)
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    return engine
