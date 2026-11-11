"""Agents: which ones Sammy has, what they're called and what they do.

AgentService only works inside a connection it's given and never opens a
transaction, so the caller can combine agent changes with others.
"""

from dataclasses import dataclass

from sqlalchemy import Connection, insert, select

from sammy.registry.tables import agents


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

    def find(self, database: Connection, short_name: str) -> Agent | None:
        """The agent with this short name, or None if there's no such agent."""
        row = database.execute(
            select(agents.c.short_name, agents.c.name, agents.c.description).where(
                agents.c.short_name == short_name
            )
        ).first()
        return Agent(*row) if row is not None else None
