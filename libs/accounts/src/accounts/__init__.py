import logging
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

from accounts.tables import ADMIN_ROLE, roles, sessions, user_roles, users

_MIGRATIONS = Path(__file__).parent / "migrations"

# Logs name users only by public_id: never by username, and never with a
# password or session token (see CLAUDE.md, Logging).
_log = logging.getLogger(__name__)


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
            self._insert_user(database, username, password)

    def set_up(self, username: str, password: str) -> None:
        """Creates the first admin: a user holding the built-in admin role."""
        with self._engine.begin() as database:
            user_id, public_id = self._insert_user(database, username, password)
            admin_role_id = database.execute(
                select(roles.c.id).where(roles.c.name == ADMIN_ROLE)
            ).scalar_one()
            database.execute(insert(user_roles).values(user_id=user_id, role_id=admin_role_id))
        _record("setup created admin", public_id)

    def roles_of(self, username: str) -> set[str]:
        """The names of the roles this user holds."""
        with self._engine.connect() as database:
            return set(
                database.execute(
                    select(roles.c.name)
                    .join(user_roles, user_roles.c.role_id == roles.c.id)
                    .join(users, users.c.id == user_roles.c.user_id)
                    .where(users.c.username == username)
                ).scalars()
            )

    def _insert_user(self, database, username: str, password: str) -> tuple[int, uuid.UUID]:
        public_id = uuid.uuid7()
        user_id = database.execute(
            insert(users)
            .values(
                public_id=public_id,
                username=username,
                password_hash=self._password_hasher.hash(password),
            )
            .returning(users.c.id)
        ).scalar_one()
        return user_id, public_id

    def log_in(self, username: str, password: str) -> Session:
        with self._engine.connect() as database:
            user = database.execute(
                select(users.c.id, users.c.public_id, users.c.password_hash).where(
                    users.c.username == username
                )
            ).one_or_none()
        # An unknown username is still checked against a stand-in hash, so it
        # takes as long to refuse as a wrong password and the response time
        # doesn't reveal which usernames exist.
        password_hash = user.password_hash if user is not None else self._unknown_user_hash
        try:
            self._password_hasher.verify(password_hash, password)
        except VerifyMismatchError:
            if user is not None:
                _record("login refused", user.public_id, level=logging.WARNING)
            else:
                # Never the username: people sometimes type their password
                # into the username box.
                _log.warning(
                    "login refused: no such user",
                    extra={"event": "login refused for unknown user"},
                )
            raise LoginRefused from None
        if user is None:
            raise LoginRefused
        session = Session(secrets.token_urlsafe(32))
        with self._engine.begin() as database:
            database.execute(
                insert(sessions).values(token_hash=_token_hash(session), user_id=user.id)
            )
        _record("login succeeded", user.public_id)
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
            public_id = database.execute(
                select(users.c.public_id)
                .join(sessions, sessions.c.user_id == users.c.id)
                .where(sessions.c.token_hash == _token_hash(session))
            ).scalar_one_or_none()
            database.execute(
                delete(sessions).where(sessions.c.token_hash == _token_hash(session))
            )
        # A session that's already gone has nobody to name.
        if public_id is not None:
            _record("logged out", public_id)


def _record(event: str, public_id: uuid.UUID, level: int = logging.INFO) -> None:
    """Logs an event about a user. The event and public id are also attached
    as fields, so they can be found without parsing the message."""
    _log.log(
        level,
        "%s: user %s",
        event,
        public_id,
        extra={"event": event, "public_id": str(public_id)},
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
