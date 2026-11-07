"""The one seam between the acceptance steps and Sammy.

Steps describe what a person does; this driver decides how that reaches
Sammy. There is no CLI or web front end yet, so it calls the accounts
library and the orchestrator directly. When a front end exists, only this
file changes.
"""

import logging

from sqlalchemy import MetaData, create_engine, func, select

from accounts import (
    Accounts,
    LoginRefused,
    Session,
    SetupAlreadyDone,
    UnknownRole,
    UsernameTaken,
)
from orchestrator_agent import LoginRequired, Orchestrator


class SammyDriver:
    def __init__(self, database_url: str):
        # Everything Sammy logs during the scenario, at every level.
        self._log = _LogRecorder()
        # A throwaway database per scenario (see drivers/database.py), so
        # scenarios can't affect each other.
        self._database_url = database_url
        self._accounts = Accounts(database_url)
        self._orchestrator = Orchestrator(self._accounts)
        self._session: Session | None = None
        self._login_refused = False
        self._asked_to_log_in = False
        self._setup_refused = False
        self._username_taken = False
        self._role_unknown = False
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
        try:
            self._accounts.create_user_as(self._session, username, password)
        except UsernameTaken:
            self._username_taken = True
            return
        self._username_taken = False
        self._passwords[username] = password

    def username_was_taken(self) -> bool:
        return self._username_taken

    def give_role(self, username: str, role: str) -> None:
        """Gives a user a role as "me"."""
        try:
            self._accounts.give_role_as(self._session, username, role)
            self._role_unknown = False
        except UnknownRole:
            self._role_unknown = True

    def role_was_unknown(self) -> bool:
        return self._role_unknown

    def can_create_users(self, username: str) -> bool:
        """Logs in as this user on the side and tries to create a user."""
        session = self._accounts.log_in(username, self._passwords[username])
        try:
            self._probes += 1
            self._accounts.create_user_as(session, f"test.probe{self._probes}", "correct-horse")
            return True
        finally:
            self._accounts.log_out(session)

    def log_in(self, username: str, password: str) -> None:
        try:
            self._session = self._accounts.log_in(username, password)
            self._login_refused = False
        except LoginRefused:
            self._session = None
            self._login_refused = True

    def log_out(self) -> None:
        # The session is deliberately kept, like a stale cookie or a copied
        # token, so the checks that follow show Sammy itself has forgotten it.
        self._accounts.log_out(self._session)

    def user_count(self) -> int:
        """How many users Sammy's database holds."""
        engine = create_engine(self._database_url)
        try:
            users = MetaData()
            users.reflect(engine, only=["users"])
            with engine.connect() as database:
                return database.execute(
                    select(func.count()).select_from(users.tables["users"])
                ).scalar_one()
        finally:
            engine.dispose()

    def run_setup(self, username: str, password: str) -> None:
        try:
            self._accounts.set_up(username, password)
            self._passwords[username] = password
            self._setup_refused = False
        except SetupAlreadyDone:
            self._setup_refused = True

    def setup_was_refused(self) -> bool:
        return self._setup_refused

    def can_log_in(self, username: str, password: str) -> bool:
        """Tries the login on the side, without changing who "I" am logged in
        as, and logs that trial session out again."""
        try:
            session = self._accounts.log_in(username, password)
        except LoginRefused:
            return False
        self._accounts.log_out(session)
        return True

    def roles_of(self, username: str) -> set[str]:
        return self._accounts.roles_of(username)

    def someone_logs_in(self, username: str) -> None:
        self.add_user(username, "correct-horse")
        self._sessions_by_user[username] = self._accounts.log_in(username, "correct-horse")

    def someone_logs_out(self, username: str) -> None:
        self._accounts.log_out(self._sessions_by_user[username])

    def is_logged_in(self, username: str) -> bool:
        return self._accounts.user_for(self._sessions_by_user[username]) == username

    def ensure_logged_out(self) -> None:
        self._session = None

    def send_message(self, message: str) -> None:
        try:
            self._orchestrator.handle(self._session, message)
            self._asked_to_log_in = False
        except LoginRequired:
            self._asked_to_log_in = True

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

    def has_recorded(self, event: str, username: str, by: str | None = None, **fields) -> bool:
        """Whether Sammy has logged this event for this user; if `by` is given,
        that this person did it; and that any other `fields` match. Logs name
        users only by public id, so the usernames are looked up first."""
        public_id = self._accounts.public_id(username)
        actor_id = self._accounts.public_id(by) if by is not None else None
        return public_id is not None and any(
            getattr(record, "event", None) == event
            and getattr(record, "public_id", None) == str(public_id)
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

    def close(self) -> None:
        self._log.stop()

    def logged_in_user(self) -> str | None:
        return self._accounts.user_for(self._session) if self._session else None

    def login_was_refused(self) -> bool:
        return self._login_refused

    def was_asked_to_log_in(self) -> bool:
        return self._asked_to_log_in


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
