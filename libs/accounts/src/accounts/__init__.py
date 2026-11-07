import secrets
import uuid
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from alembic import command
from alembic.config import Config
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import Engine, create_engine, delete, insert, select

from accounts.tables import sessions, users

_MIGRATIONS = Path(__file__).parent / "migrations"


@dataclass(frozen=True)
class Session:
    """Proof of a login, held by whoever logged in. The token is a secret, so
    it is kept out of the repr and never ends up in logs by accident."""

    token: str = field(repr=False)


class LoginRefused(Exception):
    """Raised for every failed login, whatever the reason, so the refusal
    reveals nothing about which detail was wrong."""


class Accounts:
    def __init__(self, database_url: str):
        """database_url is a SQLAlchemy URL: sqlite:///path/to/sammy.sqlite or
        postgresql+psycopg://user:password@host/database. The schema is
        brought up to date on start."""
        self._engine = create_engine(database_url)
        _migrate(self._engine)
        # Argon2id with a random salt per hash; the salt and parameters are
        # stored inside the hash string itself.
        self._password_hasher = PasswordHasher()
        # The hash of a random password nobody knows, made with the same
        # parameters as real ones.
        self._unknown_user_hash = self._password_hasher.hash(secrets.token_urlsafe(32))

    def create_user(self, username: str, password: str) -> None:
        with self._engine.begin() as database:
            database.execute(
                insert(users).values(
                    public_id=uuid.uuid7(),
                    username=username,
                    password_hash=self._password_hasher.hash(password),
                )
            )

    def log_in(self, username: str, password: str) -> Session:
        with self._engine.connect() as database:
            user = database.execute(
                select(users.c.id, users.c.password_hash).where(users.c.username == username)
            ).one_or_none()
        # An unknown username is still checked against a stand-in hash, so it
        # takes as long to refuse as a wrong password and the response time
        # doesn't reveal which usernames exist.
        password_hash = user.password_hash if user is not None else self._unknown_user_hash
        try:
            self._password_hasher.verify(password_hash, password)
        except VerifyMismatchError:
            raise LoginRefused from None
        if user is None:
            raise LoginRefused
        session = Session(secrets.token_urlsafe(32))
        with self._engine.begin() as database:
            database.execute(
                insert(sessions).values(token_hash=_token_hash(session), user_id=user.id)
            )
        return session

    def user_for(self, session: Session) -> str | None:
        """The user a session belongs to, or None once it has been logged out."""
        with self._engine.connect() as database:
            return database.execute(
                select(users.c.username)
                .join(sessions, sessions.c.user_id == users.c.id)
                .where(sessions.c.token_hash == _token_hash(session))
            ).scalar_one_or_none()

    def public_id(self, username: str) -> uuid.UUID | None:
        """How anything outside the database refers to this user, e.g. in logs.
        None if there is no such user."""
        with self._engine.connect() as database:
            return database.execute(
                select(users.c.public_id).where(users.c.username == username)
            ).scalar_one_or_none()

    def log_out(self, session: Session) -> None:
        with self._engine.begin() as database:
            database.execute(
                delete(sessions).where(sessions.c.token_hash == _token_hash(session))
            )


def _migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def _token_hash(session: Session) -> str:
    # Session tokens are long and random, so a plain SHA-256 is enough; unlike
    # passwords they don't need a slow, salted hash. Only the hash is stored,
    # so a copy of the database can't be used to take over a session.
    return sha256(session.token.encode()).hexdigest()
