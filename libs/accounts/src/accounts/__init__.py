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
from sqlalchemy import Engine, create_engine, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from accounts.tables import ADMIN_ROLE, roles, sessions, user_roles, users

_MIGRATIONS = Path(__file__).parent / "migrations"

# Permissions are fixed in code (see CLAUDE.md, Stored data). The built-in
# admin role has every one of them.
MANAGE_USERS = "manage users"
MANAGE_ROLES = "manage roles"

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


class SetupAlreadyDone(Exception):
    """Raised when setup is run on a Sammy that already has users."""


class UsernameTaken(Exception):
    """Raised when creating a user whose username is already in use."""


class UnknownRole(Exception):
    """Raised when a role is named that doesn't exist."""


class LoginRequired(Exception):
    """Raised when someone who isn't logged in tries something that needs it,
    such as talking to Sammy or managing users."""


class PermissionDenied(Exception):
    """Raised when someone tries something none of their roles allows."""


class LastManagerRequired(Exception):
    """Raised when a change would leave no active user able to manage both
    users and roles."""


class RoleAlreadyHeld(Exception):
    """Raised when giving someone a role they already hold."""


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

    def create_user_as(self, actor: Session | None, username: str, password: str) -> None:
        """Creates a user on behalf of whoever holds `actor`, and records who
        did it. The new user has no roles."""
        try:
            with self._engine.begin() as database:
                acting = _acting(database, actor)
                _require(database, acting, MANAGE_USERS)
                _, public_id = self._insert_user(database, username, password)
        except IntegrityError:
            # The unique constraint on username is the check, so two requests
            # at once can't both create the same username.
            raise UsernameTaken from None
        _record("user created", public_id, actor_public_id=acting.public_id)

    def give_role_as(self, actor: Session | None, username: str, role: str) -> None:
        """Gives a user a role on behalf of whoever holds `actor`, and records
        who did it. Refused if they already hold it."""
        try:
            with self._engine.begin() as database:
                acting = _acting(database, actor)
                # Checked first, so someone without permission can't learn which
                # users or roles exist from the refusal they get.
                _require(database, acting, MANAGE_USERS)
                user = database.execute(
                    select(users.c.id, users.c.public_id).where(users.c.username == username)
                ).one()
                role_id = database.execute(
                    select(roles.c.id).where(roles.c.name == role)
                ).scalar_one_or_none()
                if role_id is None:
                    raise UnknownRole
                database.execute(insert(user_roles).values(user_id=user.id, role_id=role_id))
        except IntegrityError:
            # user_roles' primary key is the check, as with usernames (#71).
            raise RoleAlreadyHeld from None
        _record("role given", user.public_id, actor_public_id=acting.public_id, role=role)

    def remove_role_as(self, actor: Session | None, username: str, role: str) -> None:
        """Removes a role from a user on behalf of whoever holds `actor`, and
        records who did it. It applies straight away, including to sessions
        the user already has, because permissions are checked on every
        request."""
        with self._engine.begin() as database:
            acting = _acting(database, actor)
            _require(database, acting, MANAGE_USERS)
            user = database.execute(
                select(users.c.id, users.c.public_id).where(users.c.username == username)
            ).one()
            role_id = database.execute(
                select(roles.c.id).where(roles.c.name == role)
            ).scalar_one_or_none()
            if role_id is None:
                raise UnknownRole
            database.execute(
                delete(user_roles).where(
                    user_roles.c.user_id == user.id, user_roles.c.role_id == role_id
                )
            )
            # Checked after the change, inside the transaction: raising rolls
            # the removal back.
            if not _someone_can_manage(database):
                raise LastManagerRequired
        _record("role removed", user.public_id, actor_public_id=acting.public_id, role=role)

    def disable_as(self, actor: Session | None, username: str) -> None:
        """Disables a user on behalf of whoever holds `actor`: they can't log
        in again, and every session they have ends at once. Records who did
        it."""
        with self._engine.begin() as database:
            acting = _acting(database, actor)
            _require(database, acting, MANAGE_USERS)
            user = database.execute(
                select(users.c.id, users.c.public_id).where(users.c.username == username)
            ).one()
            if not _someone_can_manage(database, excluding=user.id):
                raise LastManagerRequired
            _disable(database, user.id)
        _record("user disabled", user.public_id, actor_public_id=acting.public_id)

    def disable(self, username: str) -> None:
        """Disables a user directly, with no actor and no log entry: a building
        block for setting up a disabled user. Admins use disable_as."""
        with self._engine.begin() as database:
            user_id = database.execute(
                select(users.c.id).where(users.c.username == username)
            ).scalar_one()
            _disable(database, user_id)

    def set_up(self, username: str, password: str) -> None:
        """Creates the first admin: a user holding the built-in admin role.
        Only allowed while Sammy has no users at all."""
        with self._engine.begin() as database:
            if database.execute(select(users.c.id).limit(1)).first() is not None:
                _log.warning("setup refused: users already exist", extra={"event": "setup refused"})
                raise SetupAlreadyDone
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
                select(
                    users.c.id, users.c.public_id, users.c.password_hash, users.c.disabled
                ).where(users.c.username == username)
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
        # Refused only after the full password check, the same way as a wrong
        # password, so neither the message nor the timing shows the account is
        # disabled.
        if user.disabled:
            _record("login refused", user.public_id, level=logging.WARNING)
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
            user = _session_user(database, session)
        return user.username if user is not None else None

    def public_id(self, username: str) -> uuid.UUID | None:
        """How anything outside the database refers to this user, e.g. in logs.
        None if there is no such user."""
        with self._engine.connect() as database:
            return database.execute(
                select(users.c.public_id).where(users.c.username == username)
            ).scalar_one_or_none()

    def log_out(self, session: Session) -> None:
        with self._engine.begin() as database:
            user = _session_user(database, session)
            database.execute(
                delete(sessions).where(sessions.c.token_hash == _token_hash(session))
            )
        # A session that's already gone has nobody to name.
        if user is not None:
            _record("logged out", user.public_id)


def _session_user(database, session: Session):
    """The user a session belongs to (their id, username and public_id), or
    None if the session doesn't exist, e.g. because it has been logged out."""
    return database.execute(
        select(users.c.id, users.c.username, users.c.public_id)
        .join(sessions, sessions.c.user_id == users.c.id)
        .where(sessions.c.token_hash == _token_hash(session))
    ).one_or_none()


def _disable(database, user_id: int) -> None:
    """Marks the user disabled and ends all their sessions."""
    database.execute(update(users).where(users.c.id == user_id).values(disabled=True))
    database.execute(delete(sessions).where(sessions.c.user_id == user_id))


def _acting(database, actor: Session | None):
    """Who is acting, from their session. Refuses if they aren't logged in:
    no session, or one that has been logged out."""
    acting = _session_user(database, actor) if actor is not None else None
    if acting is None:
        raise LoginRequired
    return acting


def _can(database, user_id: int, permission: str) -> bool:
    """Whether any of the user's roles allows this. The admin role allows
    everything; other roles' permissions arrive with role management."""
    return (
        database.execute(
            select(roles.c.id)
            .join(user_roles, user_roles.c.role_id == roles.c.id)
            .where(user_roles.c.user_id == user_id, roles.c.name == ADMIN_ROLE)
        ).first()
        is not None
    )


def _someone_can_manage(database, excluding: int | None = None) -> bool:
    """Whether at least one user, other than `excluding`, can still manage
    both users and roles, so Sammy can never be locked out of its own
    administration."""
    return any(
        _can(database, user_id, MANAGE_USERS) and _can(database, user_id, MANAGE_ROLES)
        for user_id in database.execute(select(users.c.id)).scalars()
        if user_id != excluding
    )


def _require(database, acting, permission: str) -> None:
    """Refuses, and records the refusal, unless `acting` may do this."""
    if not _can(database, acting.id, permission):
        _record("permission refused", acting.public_id, level=logging.WARNING, permission=permission)
        raise PermissionDenied


def _record(
    event: str,
    public_id: uuid.UUID,
    level: int = logging.INFO,
    actor_public_id: uuid.UUID | None = None,
    **details: str,
) -> None:
    """Logs an event about a user, who did it if someone else did, and any
    details (e.g. role, permission). These are also attached as fields, so
    they can be found without parsing the message."""
    fields = {"event": event, "public_id": str(public_id)}
    message, args = "%s: user %s", [event, public_id]
    for name, value in details.items():
        fields[name] = value
        message, args = message + f" {name} %s", [*args, value]
    if actor_public_id is not None:
        fields["actor_public_id"] = str(actor_public_id)
        message, args = message + " by user %s", [*args, actor_public_id]
    _log.log(level, message, *args, extra=fields)


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
