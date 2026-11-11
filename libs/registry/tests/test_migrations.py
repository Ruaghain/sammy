from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from sammy.core import create_engine
from sammy.registry import migrate
from sammy.registry.tables import VERSION_TABLE, metadata


def test_the_migrations_build_exactly_the_schema_the_code_queries(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sammy.sqlite'}")
    try:
        migrate(engine)  # an empty database to head

        with engine.connect() as connection:
            differences = compare_metadata(
                MigrationContext.configure(connection, opts={"version_table": VERSION_TABLE}),
                metadata,
            )
    finally:
        engine.dispose()

    assert differences == []
