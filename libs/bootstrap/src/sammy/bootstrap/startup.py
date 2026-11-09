"""Starting Sammy: the one place that wires everything together.

The order matters (see CLAUDE.md, Code structure): one engine for Sammy's
whole database, each package's own tables migrated explicitly, then the
services. Every entry point (the `sammy` command, the web backend later, the
acceptance driver) starts Sammy through start().
"""

from dataclasses import dataclass

from sammy.accounts import AccountService, migrate
from sammy.agents.orchestrator import Orchestrator
from sqlalchemy import Engine, create_engine


@dataclass
class Sammy:
    engine: Engine
    accounts: AccountService
    orchestrator: Orchestrator

    def close(self) -> None:
        self.engine.dispose()


def start(database_url: str) -> Sammy:
    engine = create_engine(database_url)
    migrate(engine)
    accounts = AccountService(engine)
    return Sammy(engine=engine, accounts=accounts, orchestrator=Orchestrator(accounts))
