"""Throwaway databases for acceptance scenarios.

By default each scenario gets its own SQLite file. Set SAMMY_TEST_DATABASE_URL
to a PostgreSQL server, e.g.
    postgresql+psycopg://sammy:sammy-test@localhost:5432/postgres
and each scenario instead gets a fresh, empty database on that server,
dropped afterwards. The URL's own database is only used to create and drop
the throwaway ones.
"""

import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, make_url, text

TEST_DATABASE_URL = "SAMMY_TEST_DATABASE_URL"


@contextmanager
def throwaway_database(tmp_path: Path) -> Iterator[str]:
    """Yields the URL of an empty database that disappears afterwards."""
    server_url = os.environ.get(TEST_DATABASE_URL)
    if not server_url:
        yield f"sqlite:///{tmp_path / 'sammy.sqlite'}"
        return

    name = f"sammy_test_{secrets.token_hex(8)}"
    server = create_engine(server_url, isolation_level="AUTOCOMMIT")
    try:
        with server.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        try:
            yield make_url(server_url).set(database=name).render_as_string(
                hide_password=False
            )
        finally:
            with server.connect() as connection:
                # FORCE closes anything Sammy left connected to it.
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    finally:
        server.dispose()
