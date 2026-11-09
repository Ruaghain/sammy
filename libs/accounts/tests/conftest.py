import pytest
from sqlalchemy import create_engine

from sammy.accounts import AccountService, migrate


@pytest.fixture
def start_accounts():
    """Starts accounts on a database the way Sammy does: one engine, accounts'
    tables migrated explicitly, then the service. Calling it again on the same
    URL is a restart. Engines are disposed of afterwards."""
    engines = []

    def start(database_url: str) -> AccountService:
        engine = create_engine(database_url)
        engines.append(engine)
        migrate(engine)
        return AccountService(engine)

    yield start
    for engine in engines:
        engine.dispose()
