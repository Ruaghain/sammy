"""Starting Sammy: the one place that wires everything together.

The order matters (see CLAUDE.md, Code structure): one engine for Sammy's
whole database, each package's own tables migrated explicitly, then the
services. The web backend will reuse this.
"""

from dataclasses import dataclass

from accounts import AccountService, migrate
from orchestrator_agent import Orchestrator
from sqlalchemy import Engine, create_engine

from sammy.config import Settings


@dataclass
class Sammy:
    engine: Engine
    accounts: AccountService
    orchestrator: Orchestrator

    def close(self) -> None:
        self.engine.dispose()


def start(settings: Settings) -> Sammy:
    engine = create_engine(settings.database_url)
    migrate(engine)
    accounts = AccountService(engine)
    return Sammy(engine=engine, accounts=accounts, orchestrator=Orchestrator(accounts))
