import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_SQLITE_URL_PREFIX = "sqlite:///"


@dataclass(frozen=True)
class Session:
    username: str


class LoginRefused(Exception):
    """Raised for every failed login, whatever the reason, so the refusal
    reveals nothing about which detail was wrong."""


class Accounts:
    def __init__(self, database_url: str):
        if not database_url.startswith(_SQLITE_URL_PREFIX):
            raise ValueError(f"Expected a {_SQLITE_URL_PREFIX} database URL")
        self._database_path = database_url.removeprefix(_SQLITE_URL_PREFIX)
        # Argon2id with a random salt per hash; the salt and parameters are
        # stored inside the hash string itself.
        self._password_hasher = PasswordHasher()
        with self._database() as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                " username TEXT PRIMARY KEY,"
                " password_hash TEXT NOT NULL)"
            )

    def create_user(self, username: str, password: str) -> None:
        with self._database() as database:
            database.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, self._password_hasher.hash(password)),
            )

    def log_in(self, username: str, password: str) -> Session:
        with self._database() as database:
            # Unknown usernames aren't handled yet: that's its own scenario
            # (#15). Until then, fetchone() returns None and this unpacking
            # fails rather than quietly refusing the login.
            (password_hash,) = database.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username,)
            ).fetchone()
        try:
            self._password_hasher.verify(password_hash, password)
        except VerifyMismatchError:
            raise LoginRefused from None
        return Session(username)

    @contextmanager
    def _database(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path, autocommit=True)
        try:
            yield connection
        finally:
            connection.close()
