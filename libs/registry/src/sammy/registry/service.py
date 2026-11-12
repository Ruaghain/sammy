from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from sammy.accounts import MANAGE_AGENTS, AccountService, Session
from sammy.core import AuditLog
from sammy.registry.agents import Agent, AgentService, is_short_name
from sammy.registry.errors import (
    AgentDescriptionBlank,
    AgentNameBlank,
    AgentNameTaken,
    AgentShortNameTaken,
    InvalidShortName,
)

_audit = AuditLog("registry")


class RegistryService:
    """Everything Sammy can do with its agent registry: the only public entry
    point.

    It owns transactions and records what happens. Who is acting, and whether
    they may, comes from accounts. The SQL lives in AgentService, which works
    inside the transactions it opens.
    """

    def __init__(self, engine: Engine, accounts: AccountService):
        """`engine` is Sammy's database, shared with other packages. Its
        registry tables must already be up to date: run
        sammy.registry.migrate(engine) first, at startup."""
        self._engine = engine
        self._accounts = accounts
        self._agents = AgentService()

    def add_agent_as(
        self, actor: Session | None, short_name: str, name: str, description: str
    ) -> None:
        """Adds an agent on behalf of whoever holds `actor`, and records who
        did it. Refused if its short name isn't valid, its name or
        description is blank, or its short name or name is already in use."""
        acting = self._accounts.authorize(actor, MANAGE_AGENTS)
        if not is_short_name(short_name):
            raise InvalidShortName
        if not name.strip():
            raise AgentNameBlank
        if not description.strip():
            raise AgentDescriptionBlank
        try:
            with self._engine.begin() as database:
                self._agents.add(database, short_name, name, description)
        except IntegrityError:
            # The unique constraints on short_name and name are the check, so
            # two requests at once can't both add the same one. Which of them
            # refused is looked up afterwards, the same way on every database.
            if self.agent(short_name) is not None:
                raise AgentShortNameTaken from None
            raise AgentNameTaken from None
        _audit.record("agent added", actor_public_id=acting, agent=short_name)

    def rename_agent_as(self, actor: Session | None, short_name: str, name: str) -> None:
        """Renames an agent on behalf of whoever holds `actor`, and records who
        did it. Its short name never changes, so nothing that refers to the
        agent (e.g. a role's "use agent <SHORT_NAME>") is affected. Refused if
        the new name is blank or another agent already has it."""
        acting = self._accounts.authorize(actor, MANAGE_AGENTS)
        if not name.strip():
            raise AgentNameBlank
        try:
            with self._engine.begin() as database:
                self._agents.rename(database, short_name, name)
        except IntegrityError:
            # agents.name's unique constraint is the check, as when adding.
            raise AgentNameTaken from None
        _audit.record("agent renamed", actor_public_id=acting, agent=short_name)

    def describe_agent_as(self, actor: Session | None, short_name: str, description: str) -> None:
        """Changes an agent's description on behalf of whoever holds `actor`,
        and records who did it. Refused if the new description is blank."""
        acting = self._accounts.authorize(actor, MANAGE_AGENTS)
        if not description.strip():
            raise AgentDescriptionBlank
        with self._engine.begin() as database:
            self._agents.describe(database, short_name, description)
        _audit.record("agent described", actor_public_id=acting, agent=short_name)

    def remove_agent_as(self, actor: Session | None, short_name: str) -> None:
        """Removes an agent on behalf of whoever holds `actor`, and records
        who did it."""
        acting = self._accounts.authorize(actor, MANAGE_AGENTS)
        with self._engine.begin() as database:
            self._agents.remove(database, short_name)
        _audit.record("agent removed", actor_public_id=acting, agent=short_name)

    def add_agent(self, short_name: str, name: str, description: str) -> None:
        """Adds an agent directly, with no actor and no log entry: a building
        block for setting up agents. Admins use add_agent_as."""
        with self._engine.begin() as database:
            self._agents.add(database, short_name, name, description)

    def agent(self, short_name: str) -> Agent | None:
        """The agent with this short name, or None if there's no such agent."""
        with self._engine.connect() as database:
            return self._agents.find(database, short_name)
