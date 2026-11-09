"""Foreign keys behave the same on SQLite as on PostgreSQL: no scenario can
see the setting directly, only mistakes it would catch."""

import pytest
from sqlalchemy import exc, text

from sammy.core import create_engine, migration_connection


def sqlite_url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'sammy.sqlite'}"


def test_every_sqlite_connection_enforces_foreign_keys(tmp_path):
    engine = create_engine(sqlite_url(tmp_path))
    try:
        for _ in range(2):  # each new connection, not just the first
            with engine.connect() as connection:
                assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            engine.dispose()
    finally:
        engine.dispose()


def test_sqlite_refuses_a_row_that_points_at_nothing(tmp_path):
    engine = create_engine(sqlite_url(tmp_path))
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
            connection.execute(
                text("CREATE TABLE children (parent_id INTEGER REFERENCES parents (id))")
            )
        with pytest.raises(exc.IntegrityError), engine.begin() as connection:
            connection.execute(text("INSERT INTO children (parent_id) VALUES (1)"))
    finally:
        engine.dispose()


def make_parents_and_children(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE children (parent_id INTEGER REFERENCES parents (id))"))
        connection.execute(text("INSERT INTO parents (id) VALUES (1)"))
        connection.execute(text("INSERT INTO children (parent_id) VALUES (1)"))


def test_a_migration_can_rebuild_a_table_others_refer_to(tmp_path):
    # SQLite changes most columns by copying the table, dropping the old one
    # and renaming the copy, which a foreign key would otherwise refuse.
    engine = create_engine(sqlite_url(tmp_path))
    try:
        make_parents_and_children(engine)
        with migration_connection(engine) as connection:
            connection.execute(text("CREATE TABLE new_parents (id INTEGER PRIMARY KEY, name TEXT)"))
            connection.execute(text("INSERT INTO new_parents (id) SELECT id FROM parents"))
            connection.execute(text("DROP TABLE parents"))
            connection.execute(text("ALTER TABLE new_parents RENAME TO parents"))
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM children")).scalar_one() == 1
    finally:
        engine.dispose()


def test_a_migration_that_leaves_a_row_pointing_at_nothing_is_undone(tmp_path):
    engine = create_engine(sqlite_url(tmp_path))
    try:
        make_parents_and_children(engine)
        with pytest.raises(exc.IntegrityError), migration_connection(engine) as connection:
            connection.execute(text("DELETE FROM parents"))
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM parents")).scalar_one() == 1
    finally:
        engine.dispose()


def test_foreign_keys_are_enforced_again_after_a_migration(tmp_path):
    engine = create_engine(sqlite_url(tmp_path))
    try:
        with migration_connection(engine):
            pass
        # The pool hands the same connection out again.
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    finally:
        engine.dispose()
