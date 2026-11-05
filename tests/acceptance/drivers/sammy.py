"""The one seam between the acceptance steps and Sammy.

Steps describe what a person does; this driver decides how that reaches
Sammy. There is no CLI or web front end yet, so it calls the accounts
library and the orchestrator directly. When a front end exists, only this
file changes.
"""

from pathlib import Path

from accounts import Accounts, LoginRefused, Session
from orchestrator_agent import LoginRequired, Orchestrator


class SammyDriver:
    def __init__(self, database_dir: Path):
        # A throwaway database per scenario, so scenarios can't affect each other.
        self._accounts = Accounts(f"sqlite:///{database_dir / 'sammy.sqlite'}")
        self._orchestrator = Orchestrator(self._accounts)
        self._session: Session | None = None
        self._login_refused = False
        self._asked_to_log_in = False

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

    def ensure_logged_out(self) -> None:
        self._session = None

    def send_message(self, message: str) -> None:
        try:
            self._orchestrator.handle(self._session, message)
            self._asked_to_log_in = False
        except LoginRequired:
            self._asked_to_log_in = True

    def logged_in_user(self) -> str | None:
        return self._accounts.user_for(self._session) if self._session else None

    def login_was_refused(self) -> bool:
        return self._login_refused

    def was_asked_to_log_in(self) -> bool:
        return self._asked_to_log_in
