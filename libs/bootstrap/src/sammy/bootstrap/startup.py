"""Starting Sammy: the one place that wires everything together.

The order matters (see CLAUDE.md, Code structure): one engine for Sammy's
whole database, each package's own tables migrated explicitly, then the
services. Every entry point (the `sammy` command, the web backend later, the
acceptance driver) starts Sammy through start().
"""

from dataclasses import dataclass

from sammy import accounts, registry
from sammy.accounts import AccountService
from sammy.agents.orchestrator import Orchestrator
from sammy.core import create_engine
from sammy.registry import RegistryService
from sqlalchemy import Engine


@dataclass
class Sammy:
    engine: Engine
    accounts: AccountService
    orchestrator: Orchestrator
    registry: RegistryService

    def close(self) -> None:
        self.engine.dispose()


def start(database_url: str) -> Sammy:
    engine = create_engine(database_url)
    accounts.migrate(engine)
    registry.migrate(engine)
    account_service = AccountService(engine)
    return Sammy(
        engine=engine,
        accounts=account_service,
        orchestrator=Orchestrator(account_service),
        registry=RegistryService(engine, account_service),
    )
