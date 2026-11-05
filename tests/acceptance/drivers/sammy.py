"""The one seam between the acceptance steps and Sammy.

Steps describe what a person does; this driver decides how that reaches
Sammy. There is no CLI or web front end yet, so it calls the accounts
library directly. When a front end exists, only this file changes.
"""

from accounts import Accounts, Session


class SammyDriver:
    def __init__(self):
        self._accounts = Accounts()
        self._session: Session | None = None

    def add_user(self, username: str, password: str) -> None:
        self._accounts.create_user(username, password)

    def log_in(self, username: str, password: str) -> None:
        self._session = self._accounts.log_in(username, password)

    def logged_in_user(self) -> str | None:
        return self._session.username if self._session else None
