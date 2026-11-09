from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from sammy.accounts.tables import VERSION_TABLE, metadata


def test_the_migrations_build_exactly_the_schema_the_code_queries(tmp_path, start_accounts):
    database_url = f"sqlite:///{tmp_path / 'sammy.sqlite'}"
    start_accounts(database_url)  # migrates an empty database to head

    with create_engine(database_url).connect() as connection:
        differences = compare_metadata(
            MigrationContext.configure(connection, opts={"version_table": VERSION_TABLE}),
            metadata,
        )

    assert differences == []


def test_starting_twice_on_the_same_database_keeps_its_users(tmp_path, start_accounts):
    database_url = f"sqlite:///{tmp_path / 'sammy.sqlite'}"
    start_accounts(database_url).create_user("test.user", "correct-horse")

    session = start_accounts(database_url).log_in("test.user", "correct-horse")

    assert start_accounts(database_url).user_for(session) == "test.user"
