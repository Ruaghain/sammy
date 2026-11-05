"""The one seam between the acceptance steps and Sammy.

Steps describe what a person does; this driver decides how that reaches
Sammy. There is no CLI or web front end yet, so it calls the accounts
library directly. When a front end exists, only this file changes.
"""

from pathlib import Path

from accounts import Accounts, LoginRefused, Session


class SammyDriver:
    def __init__(self, database_dir: Path):
        # A throwaway database per scenario, so scenarios can't affect each other.
        self._accounts = Accounts(f"sqlite:///{database_dir / 'sammy.sqlite'}")
        self._session: Session | None = None
        self._login_refused = False

    def add_user(self, username: str, password: str) -> None:
        self._accounts.create_user(username, password)

    def log_in(self, username: str, password: str) -> None:
        try:
            self._session = self._accounts.log_in(username, password)
            self._login_refused = False
        except LoginRefused:
            self._session = None
            self._login_refused = True

    def logged_in_user(self) -> str | None:
        return self._session.username if self._session else None

    def login_was_refused(self) -> bool:
        return self._login_refused
