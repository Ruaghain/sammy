"""Creating Sammy's database engine.

Sammy supports SQLite and PostgreSQL, and nothing may behave differently
between them. PostgreSQL always enforces foreign keys; SQLite only does when
each connection asks it to, so every engine Sammy creates asks.

Changing the schema is the exception: SQLite changes most columns by
rebuilding the table (copy it, drop the old one, rename the copy), which
enforced foreign keys would refuse. Migrations run on migration_connection(),
which turns them off on SQLite for just that connection and checks every
reference is still sound before committing.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import sqlalchemy
from sqlalchemy import Connection, Engine, event, exc


def create_engine(database_url: str) -> Engine:
    """An engine for this database that enforces foreign keys, whichever
    database it is."""
    engine = sqlalchemy.create_engine(database_url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enforce_foreign_keys)
    return engine


def _enforce_foreign_keys(dbapi_connection, _connection_record) -> None:
    # Off by default, and set per connection. It can't change inside a
    # transaction, so it's set as the connection opens, before any begins.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


@contextmanager
def migration_connection(engine: Engine) -> Iterator[Connection]:
    """A connection for migrations, in one transaction. On SQLite, foreign
    keys aren't enforced while it's open, but the transaction is only
    committed if no row is left pointing at nothing; they're enforced again
    once it closes."""
    with engine.connect() as connection:
        sqlite = connection.dialect.name == "sqlite"
        if sqlite:
            # Only takes effect outside a transaction.
            _set_foreign_keys(connection, "OFF")
        try:
            with connection.begin():
                yield connection
                if sqlite:
                    _check_foreign_keys(connection)
        finally:
            if sqlite:
                _set_foreign_keys(connection, "ON")


def _set_foreign_keys(connection: Connection, setting: str) -> None:
    connection.exec_driver_sql(f"PRAGMA foreign_keys = {setting}")
    connection.commit()


def _check_foreign_keys(connection: Connection) -> None:
    broken = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    if broken:
        tables = sorted({row[0] for row in broken})
        raise exc.IntegrityError(
            "PRAGMA foreign_key_check",
            None,
            Exception(f"rows that point at nothing in: {', '.join(tables)}"),
        )
