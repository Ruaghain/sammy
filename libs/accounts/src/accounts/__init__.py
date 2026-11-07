import logging
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, delete, false, insert, select, update
from sqlalchemy.exc import IntegrityError

from accounts.audit import record as _record
from accounts.audit import record_about_nobody
from accounts.errors import (
    AccountsError,
    LastManagerRequired,
    LoginRefused,
    LoginRequired,
    PermissionDenied,
    RoleAlreadyHeld,
    SetupAlreadyDone,
    UnknownRole,
    UsernameTaken,
)
from accounts.passwords import check_password, hash_password, unknown_user_hash
from accounts.sessions import Session, SessionService
from accounts.tables import ADMIN_ROLE, roles, user_roles, users

__all__ = [
    "Accounts",
    "AccountsError",
    "LastManagerRequired",
    "LoginRefused",
    "LoginRequired",
    "PermissionDenied",
    "RoleAlreadyHeld",
    "Session",
    "SetupAlreadyDone",
    "UnknownRole",
    "UsernameTaken",
]

_MIGRATIONS = Path(__file__).parent / "migrations"

# Permissions are fixed in code (see CLAUDE.md, Stored data). The built-in
# admin role has every one of them.
MANAGE_USERS = "manage users"
MANAGE_ROLES = "manage roles"


class Accounts:
    def __init__(self, database_url: str):
        """database_url is a SQLAlchemy URL: sqlite:///path/to/sammy.sqlite or
        postgresql+psycopg://user:password@host/database. The schema is
        brought up to date on start."""
        self._engine = create_engine(database_url)
        _migrate(self._engine)
        self._sessions = SessionService()

    def create_user(self, username: str, password: str) -> None:
        with self._engine.begin() as database:
            self._insert_user(database, username, password)

    def create_user_as(self, actor: Session | None, username: str, password: str) -> None:
        """Creates a user on behalf of whoever holds `actor`, and records who
        did it. The new user has no roles."""
        try:
            with self._engine.begin() as database:
                acting = self._acting(database, actor)
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
                acting = self._acting(database, actor)
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
            acting = self._acting(database, actor)
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
            acting = self._acting(database, actor)
            _require(database, acting, MANAGE_USERS)
            user = database.execute(
                select(users.c.id, users.c.public_id).where(users.c.username == username)
            ).one()
            if not _someone_can_manage(database, excluding=user.id):
                raise LastManagerRequired
            self._disable(database, user.id)
        _record("user disabled", user.public_id, actor_public_id=acting.public_id)

    def give_role(self, username: str, role: str) -> None:
        """Gives a user a role directly, with no actor and no log entry: a
        building block for setting up users. Admins use give_role_as."""
        with self._engine.begin() as database:
            user_id = database.execute(
                select(users.c.id).where(users.c.username == username)
            ).scalar_one()
            role_id = database.execute(select(roles.c.id).where(roles.c.name == role)).scalar_one()
            database.execute(insert(user_roles).values(user_id=user_id, role_id=role_id))

    def disable(self, username: str) -> None:
        """Disables a user directly, with no actor and no log entry: a building
        block for setting up a disabled user. Admins use disable_as."""
        with self._engine.begin() as database:
            user_id = database.execute(
                select(users.c.id).where(users.c.username == username)
            ).scalar_one()
            self._disable(database, user_id)

    def set_up(self, username: str, password: str) -> None:
        """Creates the first admin: a user holding the built-in admin role.
        Only allowed while Sammy has no users at all."""
        with self._engine.begin() as database:
            if database.execute(select(users.c.id).limit(1)).first() is not None:
                record_about_nobody(
                    "setup refused", "setup refused: users already exist", level=logging.WARNING
                )
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

    def _acting(self, database, actor: Session | None):
        """Who is acting, from their session. Refuses if they aren't logged in:
        no session, or one that has been logged out."""
        acting = self._sessions.owner(database, actor) if actor is not None else None
        if acting is None:
            raise LoginRequired
        return acting

    def _disable(self, database, user_id: int) -> None:
        """Marks the user disabled and ends all their sessions."""
        database.execute(update(users).where(users.c.id == user_id).values(disabled=True))
        self._sessions.end_all_for(database, user_id)

    def _insert_user(self, database, username: str, password: str) -> tuple[int, uuid.UUID]:
        public_id = uuid.uuid7()
        user_id = database.execute(
            insert(users)
            .values(
                public_id=public_id,
                username=username,
                password_hash=hash_password(password),
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
        password_hash = user.password_hash if user is not None else unknown_user_hash()
        if not check_password(password_hash, password):
            if user is not None:
                _record("login refused", user.public_id, level=logging.WARNING)
            else:
                # Never the username: people sometimes type their password
                # into the username box.
                record_about_nobody(
                    "login refused for unknown user",
                    "login refused: no such user",
                    level=logging.WARNING,
                )
            raise LoginRefused
        if user is None:
            raise LoginRefused
        # Refused only after the full password check, the same way as a wrong
        # password, so neither the message nor the timing shows the account is
        # disabled.
        if user.disabled:
            _record("login refused", user.public_id, level=logging.WARNING)
            raise LoginRefused
        with self._engine.begin() as database:
            session = self._sessions.start(database, user.id)
        _record("login succeeded", user.public_id)
        return session

    def user_for(self, session: Session) -> str | None:
        """The user a session belongs to, or None once it has been logged out."""
        with self._engine.connect() as database:
            user = self._sessions.owner(database, session)
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
            user = self._sessions.owner(database, session)
            self._sessions.end(database, session)
        # A session that's already gone has nobody to name.
        if user is not None:
            _record("logged out", user.public_id)


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
    """Whether at least one active user, other than `excluding`, can still
    manage both users and roles, so Sammy can never be locked out of its own
    administration. Disabled users can't log in, so they don't count."""
    active_users = select(users.c.id).where(users.c.disabled == false())
    return any(
        _can(database, user_id, MANAGE_USERS) and _can(database, user_id, MANAGE_ROLES)
        for user_id in database.execute(active_users).scalars()
        if user_id != excluding
    )


def _require(database, acting, permission: str) -> None:
    """Refuses, and records the refusal, unless `acting` may do this."""
    if not _can(database, acting.id, permission):
        _record("permission refused", acting.public_id, level=logging.WARNING, permission=permission)
        raise PermissionDenied


def _migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
