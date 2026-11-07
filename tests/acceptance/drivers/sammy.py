"""The one seam between the acceptance steps and Sammy.

Steps describe what a person does; this driver decides how that reaches
Sammy. There is no CLI or web front end yet, so it calls the accounts
library and the orchestrator directly. When a front end exists, only this
file changes.
"""

import logging

from sqlalchemy import MetaData, create_engine, select

from accounts import Accounts, LoginRefused, Session
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
        # Sessions of other people, by username, for scenarios with several
        # people logged in at once.
        self._sessions_by_user: dict[str, Session] = {}

    def add_user(self, username: str, password: str) -> None:
        self._accounts.create_user(username, password)

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

    def has_recorded(self, event: str, username: str) -> bool:
        """Whether Sammy has logged this event for this user. Logs name users
        only by public id, so the username is looked up first."""
        public_id = self._accounts.public_id(username)
        return public_id is not None and any(
            getattr(record, "event", None) == event
            and getattr(record, "public_id", None) == str(public_id)
            for record in self._log.records()
        )

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
        formatter = logging.Formatter("%(name)s %(levelname)s %(message)s")
        return [formatter.format(record) for record in self._records]

    def stop(self) -> None:
        self._root.removeHandler(self)
        self._root.setLevel(self._previous_level)
