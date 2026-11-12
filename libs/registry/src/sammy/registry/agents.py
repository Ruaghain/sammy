"""Agents: which ones Sammy has, what they're called and what they do.

AgentService only works inside a connection it's given and never opens a
transaction, so the caller can combine agent changes with others.
"""

import re
from dataclasses import dataclass

from sqlalchemy import Connection, delete, insert, select, update

from sammy.registry.tables import agents

# Capital letters, digits and underscores, starting with a letter, so it can
# go into an environment variable name (SAMMY_<SHORT_NAME>_MODEL).
_SHORT_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


def is_short_name(short_name: str) -> bool:
    """Whether this can be an agent's short name."""
    return _SHORT_NAME.fullmatch(short_name) is not None


@dataclass(frozen=True)
class Agent:
    short_name: str
    name: str
    description: str


class AgentService:
    def add(self, database: Connection, short_name: str, name: str, description: str) -> None:
        database.execute(
            insert(agents).values(short_name=short_name, name=name, description=description)
        )

    def rename(self, database: Connection, short_name: str, name: str) -> None:
        database.execute(update(agents).where(agents.c.short_name == short_name).values(name=name))

    def describe(self, database: Connection, short_name: str, description: str) -> None:
        database.execute(
            update(agents).where(agents.c.short_name == short_name).values(description=description)
        )

    def remove(self, database: Connection, short_name: str) -> None:
        database.execute(delete(agents).where(agents.c.short_name == short_name))

    def find(self, database: Connection, short_name: str) -> Agent | None:
        """The agent with this short name, or None if there's no such agent."""
        row = database.execute(
            select(agents.c.short_name, agents.c.name, agents.c.description).where(
                agents.c.short_name == short_name
            )
        ).first()
        return Agent(*row) if row is not None else None
