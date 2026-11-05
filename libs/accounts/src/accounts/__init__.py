from dataclasses import dataclass


@dataclass(frozen=True)
class Session:
    username: str


class Accounts:
    # Deliberately minimal: no scenario yet needs a user to be stored, looked
    # up or have their password checked. Doing any of that now would turn the
    # wrong-password and unknown-user scenarios green before they are built.

    def create_user(self, username: str, password: str) -> None:
        pass

    def log_in(self, username: str, password: str) -> Session:
        return Session(username)
