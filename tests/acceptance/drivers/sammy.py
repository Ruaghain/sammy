"""The one seam between the acceptance steps and Sammy.

Steps describe what a person does; this driver decides how that reaches
Sammy. There is no CLI or web front end yet, so it calls the accounts
library and the orchestrator directly. When a front end exists, only this
file changes.
"""

import logging

from sqlalchemy import MetaData, create_engine, func, select

from sammy.accounts import (
    AccountsError,
    AdminRoleIsFixed,
    LastManagerRequired,
    LoginRefused,
    LoginRequired,
    PermissionDenied,
    RoleAlreadyHeld,
    RoleInUse,
    RoleNameTaken,
    Session,
    SetupAlreadyDone,
    UnknownPermission,
    UnknownRole,
    UsernameTaken,
)
from sammy.bootstrap import start
from sammy.registry import (
    AgentDescriptionBlank,
    AgentInUse,
    AgentNameBlank,
    AgentNameTaken,
    AgentShortNameTaken,
    InvalidShortName,
    RegistryError,
)

# Everything Sammy can refuse with. The driver notes each refusal for the
# Then steps to ask about, rather than letting it fail the step.
_REFUSALS = (AccountsError, RegistryError)


class SammyDriver:
    def __init__(self, database_url: str):
        # Everything Sammy logs during the scenario, at every level.
        self._log = _LogRecorder()
        # A throwaway database per scenario (see drivers/database.py), so
        # scenarios can't affect each other.
        self._database_url = database_url
        # Started exactly the way every entry point starts Sammy.
        self._sammy = start(database_url)
        self._accounts = self._sammy.accounts
        self._orchestrator = self._sammy.orchestrator
        self._registry = self._sammy.registry
        self._session: Session | None = None
        self._my_username: str | None = None
        # Every refusal Sammy gave "me" during the scenario, oldest first.
        # Then steps ask whether a given kind of refusal happened.
        self._refusals: list[Exception] = []
        # The refusals a Then step has asked about. Any other refusal was
        # unexpected, and fails the scenario when it ends (see close()).
        self._expected: set[int] = set()
        # Passwords of the users this driver created, so it can act as them.
        self._passwords: dict[str, str] = {}
        self._probes = 0
        # Sessions of other people, by username, for scenarios with several
        # people logged in at once.
        self._sessions_by_user: dict[str, Session] = {}

    def add_user(self, username: str, password: str) -> None:
        self._accounts.create_user(username, password)
        self._passwords[username] = password

    def create_user(self, username: str, password: str) -> None:
        """Creates a user as "me", whoever I'm logged in as."""
        if self._attempt(lambda: self._accounts.create_user_as(self._session, username, password)):
            self._passwords[username] = password

    def username_was_taken(self) -> bool:
        return self._was_refused(UsernameTaken)

    def permission_was_denied(self) -> bool:
        return self._was_refused(PermissionDenied)

    def user_exists(self, username: str) -> bool:
        return self._accounts.public_id(username) is not None

    def give_role(self, username: str, role: str) -> None:
        """Gives a user a role as "me"."""
        self._attempt(lambda: self._accounts.give_role_as(self._session, username, role))

    def disable(self, username: str) -> None:
        """Disables a user as "me"."""
        self._attempt(lambda: self._accounts.disable_as(self._session, username))

    def remove_role(self, username: str, role: str) -> None:
        """Removes a role from a user as "me"."""
        self._attempt(lambda: self._accounts.remove_role_as(self._session, username, role))

    def last_manager_was_protected(self) -> bool:
        return self._was_refused(LastManagerRequired)

    def role_was_already_held(self) -> bool:
        return self._was_refused(RoleAlreadyHeld)

    def role_was_unknown(self) -> bool:
        return self._was_refused(UnknownRole)

    def create_role(self, role: str, permissions: str) -> None:
        """Creates a role as "me", from a phrase such as "manage users" or
        "manage users and roles"."""
        self._attempt(
            lambda: self._accounts.create_role_as(self._session, role, _permission_names(permissions))
        )

    def permission_was_unknown(self) -> bool:
        return self._was_refused(UnknownPermission)

    def role_name_was_taken(self) -> bool:
        return self._was_refused(RoleNameTaken)

    def permissions_of(self, role: str) -> set[str]:
        return self._accounts.permissions_of(role)

    def role_allows_only(self, role: str, permissions: str) -> bool:
        """Whether the role grants exactly what a phrase such as "managing
        users" says: nothing missing and nothing extra."""
        return self.permissions_of(role) == set(_permission_names_doing(permissions))

    def has_role(self, role: str, permissions: str) -> None:
        """Sets up a role directly, as a Given; creating a role as an admin
        goes through create_role()."""
        self._accounts.create_role(role, _permission_names(permissions))

    def grant(self, role: str, permissions: str) -> None:
        """Lets a role do more, as "me", from a phrase such as "manage users"."""
        self._attempt(lambda: self._accounts.grant_as(self._session, role, _permission_names(permissions)))

    def revoke(self, role: str, permissions: str) -> None:
        """Stops a role doing something, as "me", from a phrase such as
        "managing users"."""
        self._attempt(
            lambda: self._accounts.revoke_as(self._session, role, _permission_names_doing(permissions))
        )

    def delete_role(self, role: str) -> None:
        """Deletes a role as "me"."""
        self._attempt(lambda: self._accounts.delete_role_as(self._session, role))

    def role_was_in_use(self) -> bool:
        return self._was_refused(RoleInUse)

    def role_exists(self, role: str) -> bool:
        return self._accounts.role_exists(role)

    def admin_role_was_protected(self) -> bool:
        return self._was_refused(AdminRoleIsFixed)

    def has_recorded_for_each(
        self, permissions: str, event: str, phrased_as: str = "do", **fields
    ) -> bool:
        """has_recorded, once for each permission the phrase names; the phrase
        is "manage users" style ("do") or "managing users" style ("doing")."""
        names = _permission_names_doing(permissions) if phrased_as == "doing" else _permission_names(permissions)
        return all(self.has_recorded(event, permission=permission, **fields) for permission in names)

    def can_create_roles(self, username: str) -> bool:
        """Tries to create a role as this person, as can_create_users does for
        users."""
        return self._can_as(
            username, lambda session, n: self._accounts.create_role_as(session, f"test.probe-role{n}", [])
        )

    def can_create_users(self, username: str) -> bool:
        """Tries to create a user as this person: through the session they're
        already logged in with, if any, otherwise a login on the side."""
        return self._can_as(
            username,
            lambda session, n: self._accounts.create_user_as(session, f"test.probe{n}", "correct-horse"),
        )

    def _can_as(self, username: str, attempt) -> bool:
        existing = self._sessions_by_user.get(username)
        if existing is None and self._session is not None and self._my_username == username:
            # "Me": the session I logged in with, even if Sammy has since
            # ended it (that's exactly what this check should catch).
            existing = self._session
        session = existing or self._accounts.log_in(username, self._passwords[username])
        try:
            self._probes += 1
            attempt(session, self._probes)
            return True
        except (PermissionDenied, LoginRequired):
            return False
        finally:
            if existing is None:
                self._accounts.log_out(session)

    def add_agent(self, short_name: str, name: str, description: str) -> None:
        """Adds an agent to the registry as "me"."""
        self._attempt(
            lambda: self._registry.add_agent_as(self._session, short_name, name, description)
        )

    def rename_agent(self, short_name: str, name: str) -> None:
        """Renames an agent as "me"."""
        self._attempt(lambda: self._registry.rename_agent_as(self._session, short_name, name))

    def describe_agent(self, short_name: str, description: str) -> None:
        """Changes an agent's description as "me"."""
        self._attempt(
            lambda: self._registry.describe_agent_as(self._session, short_name, description)
        )

    def remove_agent(self, short_name: str) -> None:
        """Removes an agent as "me"."""
        self._attempt(lambda: self._registry.remove_agent_as(self._session, short_name))

    def has_agent(self, short_name: str, name: str, description: str) -> None:
        """Sets up an agent directly, as a Given; adding one as an admin goes
        through add_agent()."""
        self._registry.add_agent(short_name, name, description)

    def agent_field_taken(self) -> str | None:
        """Which of an agent's details I was told is already taken, if any:
        "short name" or "name"."""
        return self._field_refused({AgentShortNameTaken: "short name", AgentNameTaken: "name"})

    def agent_field_blank(self) -> str | None:
        """Which of an agent's details I was told can't be blank, if any."""
        return self._field_refused({AgentNameBlank: "name", AgentDescriptionBlank: "description"})

    def agent_was_in_use(self) -> bool:
        return self._was_refused(AgentInUse)

    def short_name_was_invalid(self) -> bool:
        return self._was_refused(InvalidShortName)

    def agent_count(self) -> int:
        """How many agents Sammy's database holds."""
        return self._row_count("agents")

    def agent(self, short_name: str) -> tuple[str, str] | None:
        """The agent's name and description, or None if there's no such agent."""
        agent = self._registry.agent(short_name)
        return (agent.name, agent.description) if agent is not None else None

    def log_in(self, username: str, password: str) -> None:
        self._session = None

        def log_in():
            self._session = self._accounts.log_in(username, password)
            self._my_username = username

        self._attempt(log_in)

    def log_out(self) -> None:
        # The session is deliberately kept, like a stale cookie or a copied
        # token, so the checks that follow show Sammy itself has forgotten it.
        self._accounts.log_out(self._session)

    def user_count(self) -> int:
        """How many users Sammy's database holds."""
        return self._row_count("users")

    def _row_count(self, table: str) -> int:
        """How many rows one of Sammy's tables holds, read straight from the
        database rather than through Sammy."""
        engine = create_engine(self._database_url)
        try:
            tables = MetaData()
            tables.reflect(engine, only=[table])
            with engine.connect() as database:
                return database.execute(
                    select(func.count()).select_from(tables.tables[table])
                ).scalar_one()
        finally:
            engine.dispose()

    def has_been_disabled(self, username: str) -> None:
        """Sets up a disabled user directly, as a Given; disabling as an admin
        goes through disable()."""
        self._accounts.disable(username)

    def has_been_given_role(self, username: str, role: str) -> None:
        """Sets up a user's role directly, as a Given; giving a role as an
        admin goes through give_role()."""
        self._accounts.give_role(username, role)

    def run_setup(self, username: str, password: str) -> None:
        if self._attempt(lambda: self._accounts.set_up(username, password)):
            self._passwords[username] = password

    def setup_was_refused(self) -> bool:
        return self._was_refused(SetupAlreadyDone)

    def can_log_in(self, username: str, password: str) -> bool:
        """Tries the login on the side, without changing who "I" am logged in
        as, and logs that trial session out again."""
        try:
            session = self._accounts.log_in(username, password)
        except LoginRefused:
            return False
        self._accounts.log_out(session)
        return True

    def can_log_in_with_their_password(self, username: str) -> bool:
        """can_log_in, using the password this driver gave the user."""
        return self.can_log_in(username, self._passwords[username])

    def roles_of(self, username: str) -> set[str]:
        return self._accounts.roles_of(username)

    def someone_logs_in(self, username: str) -> None:
        self.add_user(username, "correct-horse")
        self._sessions_by_user[username] = self._accounts.log_in(username, "correct-horse")
        self._passwords[username] = "correct-horse"

    def someone_logs_out(self, username: str) -> None:
        self._accounts.log_out(self._sessions_by_user[username])

    def is_logged_in(self, username: str) -> bool:
        return self._accounts.user_for(self._sessions_by_user[username]) == username

    def ensure_logged_out(self) -> None:
        self._session = None

    def send_message(self, message: str) -> None:
        self._attempt(lambda: self._orchestrator.handle(self._session, message))

    def my_session_token(self) -> str:
        """The secret token of the current login, as a front end would hold it."""
        assert self._session is not None, "not logged in"
        return self._session.token

    def everything_recorded(self) -> str:
        """Everything Sammy has written down: every value in every table of its
        database, and every log record, as one block of text to search."""
        engine = create_engine(self._database_url)
        try:
            tables = MetaData()
            tables.reflect(engine)
            with engine.connect() as database:
                values = [
                    str(value)
                    for table in tables.sorted_tables
                    for row in database.execute(select(table))
                    for value in row
                ]
        finally:
            engine.dispose()
        return "\n".join(values + self._log.lines())

    def has_recorded(
        self, event: str, username: str | None = None, by: str | None = None, **fields
    ) -> bool:
        """Whether Sammy has logged this event; if `username` is given, about
        that user; if `by` is given, that this person did it; and that any
        other `fields` match. Logs name users only by public id, so the
        usernames are looked up first."""
        public_id = self._accounts.public_id(username) if username is not None else None
        actor_id = self._accounts.public_id(by) if by is not None else None
        if (username is not None and public_id is None) or (by is not None and actor_id is None):
            return False
        return any(
            getattr(record, "event", None) == event
            and (username is None or getattr(record, "public_id", None) == str(public_id))
            and (by is None or getattr(record, "actor_public_id", None) == str(actor_id))
            and all(getattr(record, name, None) == value for name, value in fields.items())
            for record in self._log.records()
        )

    def has_recorded_about_nobody(self, event: str) -> bool:
        """Whether Sammy has logged this event without naming any user."""
        return any(
            getattr(record, "event", None) == event
            and getattr(record, "public_id", None) is None
            for record in self._log.records()
        )

    def everything_logged(self) -> str:
        """Every log line Sammy has written, without the database."""
        return "\n".join(self._log.lines())

    def unexpected_refusals(self) -> list[Exception]:
        """Refusals no Then step asked about: Sammy refused something the
        scenario expected to work."""
        # A refused login is an outcome login scenarios set up on purpose, and
        # check through who is logged in and what Sammy recorded, so it never
        # counts as unexpected.
        return [
            refusal
            for refusal in self._refusals
            if id(refusal) not in self._expected and not isinstance(refusal, LoginRefused)
        ]

    def close(self) -> None:
        self._log.stop()
        self._sammy.close()

    def logged_in_user(self) -> str | None:
        return self._accounts.user_for(self._session) if self._session else None

    def login_was_refused(self) -> bool:
        return self._was_refused(LoginRefused)

    def was_asked_to_log_in(self) -> bool:
        return self._was_refused(LoginRequired)

    def _attempt(self, action) -> bool:
        """Does something as "me". If Sammy refuses, notes the refusal for the
        Then steps instead of failing the step. Whether it was done."""
        try:
            action()
        except _REFUSALS as refusal:
            self._refusals.append(refusal)
            return False
        return True

    def _was_refused(self, kind: type[Exception]) -> bool:
        """Whether Sammy refused me with this kind of refusal at any point in
        the scenario."""
        matching = [refusal for refusal in self._refusals if isinstance(refusal, kind)]
        self._expected.update(map(id, matching))
        return bool(matching)

    def _field_refused(self, fields: dict[type[Exception], str]) -> str | None:
        """Which field the most recent of these refusals was about, if any."""
        for refusal in reversed(self._refusals):
            for kind, field in fields.items():
                if isinstance(refusal, kind):
                    self._expected.add(id(refusal))
                    return field
        return None


class _LogRecorder(logging.Handler):
    """Captures every log record from any logger while it's installed, except
    the test tooling's own. Libraries Sammy uses (SQLAlchemy, Alembic,
    psycopg, ...) still count: if they log a secret, Sammy has recorded it."""

    _TEST_TOOLING = ("pytest_bdd", "_pytest", "pytest")

    def __init__(self):
        super().__init__(level=logging.NOTSET)
        self._records: list[logging.LogRecord] = []
        self._root = logging.getLogger()
        self._previous_level = self._root.level
        self._root.addHandler(self)
        self._root.setLevel(logging.NOTSET)

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.split(".")[0] not in self._TEST_TOOLING:
            self._records.append(record)

    def records(self) -> list[logging.LogRecord]:
        return list(self._records)

    def lines(self) -> list[str]:
        """Each record as text: its message plus any extra fields attached to
        it, since a log file's format may print those too."""
        formatter = logging.Formatter("%(name)s %(levelname)s %(message)s")
        return [
            " ".join([formatter.format(record), *map(str, _extra_fields(record).values())])
            for record in self._records
        ]

    def stop(self) -> None:
        self._root.removeHandler(self)
        self._root.setLevel(self._previous_level)


_STANDARD_RECORD_FIELDS = set(vars(logging.makeLogRecord({})))


def _extra_fields(record: logging.LogRecord) -> dict:
    return {
        name: value
        for name, value in vars(record).items()
        if name not in _STANDARD_RECORD_FIELDS and name not in ("message", "asctime")
    }


def _permission_names(phrase: str) -> list[str]:
    """Turns how a scenario says it ("manage users", "manage users and roles",
    "view agents", 'use the agent "homework"') into Sammy's permission names
    ("manage users", "manage roles", "use agent homework", ...)."""
    if phrase == "no permissions":
        return []
    verb, _, rest = phrase.partition(" ")
    if verb == "use" and rest.startswith('the agent "'):
        return [f"use agent {rest.removeprefix('the agent ').strip('\"')}"]
    return [f"{verb} {thing.strip()}" for thing in rest.split(" and ")]


def _permission_names_doing(phrase: str) -> list[str]:
    """As _permission_names, for phrases such as "managing users and roles"
    or 'using the agent "homework"'."""
    verb, _, rest = phrase.partition(" ")
    plain = {"managing": "manage", "viewing": "view", "using": "use"}.get(verb, verb)
    return _permission_names(f"{plain} {rest}")
