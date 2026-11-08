import logging
import uuid

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from accounts.audit import record as _record
from accounts.audit import record_about_nobody
from accounts.errors import (
    AdminRoleIsFixed,
    LastManagerRequired,
    LoginRefused,
    LoginRequired,
    PermissionDenied,
    RoleAlreadyHeld,
    RoleInUse,
    RoleNameTaken,
    SetupAlreadyDone,
    UnknownRole,
    UsernameTaken,
)
from accounts.passwords import check_password, unknown_user_hash
from accounts.roles import MANAGE_ROLES, MANAGE_USERS, RoleService
from accounts.sessions import Session, SessionService
from accounts.tables import ADMIN_ROLE
from accounts.users import UserService


class AccountService:
    """Everything Sammy can do with accounts: the only public entry point.

    It owns transactions, works out who is acting and whether they're allowed,
    enforces rules that span users and roles (someone can always manage both),
    and records what happens. The SQL lives in UserService, RoleService and
    SessionService, which work inside the transactions it opens.
    """

    def __init__(self, engine: Engine):
        """`engine` is Sammy's database, created by whatever starts Sammy and
        shared with other packages. Its accounts tables must already be up to
        date: run accounts.migrate(engine) first, at startup."""
        self._engine = engine
        self._sessions = SessionService()
        self._users = UserService()
        self._roles = RoleService()

    def create_user(self, username: str, password: str) -> None:
        with self._engine.begin() as database:
            self._users.create(database, username, password)

    def create_user_as(self, actor: Session | None, username: str, password: str) -> None:
        """Creates a user on behalf of whoever holds `actor`, and records who
        did it. The new user has no roles."""
        try:
            with self._engine.begin() as database:
                acting = self._acting(database, actor)
                self._require(database, acting, MANAGE_USERS)
                _, public_id = self._users.create(database, username, password)
        except IntegrityError:
            # The unique constraint on username is the check, so two requests
            # at once can't both create the same username.
            raise UsernameTaken from None
        _record("user created", public_id, actor_public_id=acting.public_id)

    def create_role_as(self, actor: Session | None, name: str, permissions: list[str]) -> None:
        """Creates a role granting these permissions, on behalf of whoever
        holds `actor`, and records who did it."""
        try:
            with self._engine.begin() as database:
                acting = self._acting(database, actor)
                self._require(database, acting, MANAGE_ROLES)
                self._roles.create(database, name, permissions)
        except IntegrityError:
            # roles.name's unique constraint is the check, as with usernames.
            raise RoleNameTaken from None
        _record("role created", actor_public_id=acting.public_id, role=name)

    def grant_as(self, actor: Session | None, role: str, permissions: list[str]) -> None:
        """Lets a role do more, on behalf of whoever holds `actor`, and records
        who did it. It applies straight away, including to sessions its
        holders already have, because permissions are checked on every
        request."""
        with self._engine.begin() as database:
            acting = self._acting(database, actor)
            self._require(database, acting, MANAGE_ROLES)
            role_id = self._roles.find_id(database, role)
            if role_id is None:
                raise UnknownRole
            for permission in permissions:
                self._roles.grant(database, role_id, permission)
        for permission in permissions:
            _record(
                "permission granted",
                actor_public_id=acting.public_id,
                role=role,
                permission=permission,
            )

    def revoke_as(self, actor: Session | None, role: str, permissions: list[str]) -> None:
        """Stops a role doing something, on behalf of whoever holds `actor`, and
        records who did it. It applies straight away, including to sessions its
        holders already have."""
        with self._engine.begin() as database:
            acting = self._acting(database, actor)
            self._require(database, acting, MANAGE_ROLES)
            if role == ADMIN_ROLE:
                # Always has every permission (see CLAUDE.md, Stored data).
                raise AdminRoleIsFixed
            role_id = self._roles.find_id(database, role)
            if role_id is None:
                raise UnknownRole
            for permission in permissions:
                self._roles.revoke(database, role_id, permission)
        for permission in permissions:
            _record(
                "permission revoked",
                actor_public_id=acting.public_id,
                role=role,
                permission=permission,
            )

    def delete_role_as(self, actor: Session | None, role: str) -> None:
        """Deletes a role nobody holds, on behalf of whoever holds `actor`, and
        records who did it. The built-in admin role can never be deleted."""
        with self._engine.begin() as database:
            acting = self._acting(database, actor)
            self._require(database, acting, MANAGE_ROLES)
            if role == ADMIN_ROLE:
                raise AdminRoleIsFixed
            role_id = self._roles.find_id(database, role)
            if role_id is None:
                raise UnknownRole
            # Refused rather than taking the role away from its holders.
            if self._roles.is_held(database, role_id):
                raise RoleInUse
            self._roles.delete(database, role_id)
        _record("role deleted", actor_public_id=acting.public_id, role=role)

    def permissions_of(self, role: str) -> set[str]:
        """What a role grants, or an empty set if there's no such role."""
        with self._engine.connect() as database:
            role_id = self._roles.find_id(database, role)
            return self._roles.permissions(database, role_id) if role_id is not None else set()

    def role_exists(self, role: str) -> bool:
        """Whether a role with this name exists."""
        with self._engine.connect() as database:
            return self._roles.find_id(database, role) is not None

    def give_role_as(self, actor: Session | None, username: str, role: str) -> None:
        """Gives a user a role on behalf of whoever holds `actor`, and records
        who did it. Refused if they already hold it."""
        try:
            with self._engine.begin() as database:
                acting = self._acting(database, actor)
                # Checked first, so someone without permission can't learn which
                # users or roles exist from the refusal they get.
                self._require(database, acting, MANAGE_USERS)
                user = self._users.find(database, username)
                role_id = self._roles.find_id(database, role)
                if role_id is None:
                    raise UnknownRole
                self._roles.give(database, user.id, role_id)
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
            self._require(database, acting, MANAGE_USERS)
            user = self._users.find(database, username)
            role_id = self._roles.find_id(database, role)
            if role_id is None:
                raise UnknownRole
            self._roles.remove(database, user.id, role_id)
            # Checked after the change, inside the transaction: raising rolls
            # the removal back.
            if not self._roles.someone_can_manage(database, self._users.active_ids(database)):
                raise LastManagerRequired
        _record("role removed", user.public_id, actor_public_id=acting.public_id, role=role)

    def disable_as(self, actor: Session | None, username: str) -> None:
        """Disables a user on behalf of whoever holds `actor`: they can't log
        in again, and every session they have ends at once. Records who did
        it."""
        with self._engine.begin() as database:
            acting = self._acting(database, actor)
            self._require(database, acting, MANAGE_USERS)
            user = self._users.find(database, username)
            if not self._roles.someone_can_manage(
                database, self._users.active_ids(database), excluding=user.id
            ):
                raise LastManagerRequired
            self._disable(database, user.id)
        _record("user disabled", user.public_id, actor_public_id=acting.public_id)

    def create_role(self, name: str, permissions: list[str]) -> None:
        """Creates a role directly, with no actor and no log entry: a building
        block for setting up roles. Admins use create_role_as."""
        with self._engine.begin() as database:
            self._roles.create(database, name, permissions)

    def give_role(self, username: str, role: str) -> None:
        """Gives a user a role directly, with no actor and no log entry: a
        building block for setting up users. Admins use give_role_as."""
        with self._engine.begin() as database:
            user_id = self._users.find(database, username).id
            self._roles.give(database, user_id, self._roles.find_id(database, role))

    def disable(self, username: str) -> None:
        """Disables a user directly, with no actor and no log entry: a building
        block for setting up a disabled user. Admins use disable_as."""
        with self._engine.begin() as database:
            user_id = self._users.find(database, username).id
            self._disable(database, user_id)

    def set_up(self, username: str, password: str) -> None:
        """Creates the first admin: a user holding the built-in admin role.
        Only allowed while Sammy has no users at all."""
        with self._engine.begin() as database:
            if self._users.any_exist(database):
                record_about_nobody(
                    "setup refused", "setup refused: users already exist", level=logging.WARNING
                )
                raise SetupAlreadyDone
            user_id, public_id = self._users.create(database, username, password)
            self._roles.give(database, user_id, self._roles.find_id(database, ADMIN_ROLE))
        _record("setup created admin", public_id)

    def roles_of(self, username: str) -> set[str]:
        """The names of the roles this user holds."""
        with self._engine.connect() as database:
            user = self._users.find(database, username)
            return self._roles.names_of(database, user.id) if user is not None else set()

    def _require(self, database, acting, permission: str) -> None:
        """Refuses, and records the refusal, unless `acting` may do this."""
        if not self._roles.can(database, acting.id, permission):
            _record("permission refused", acting.public_id, level=logging.WARNING, permission=permission)
            raise PermissionDenied

    def _acting(self, database, actor: Session | None):
        """Who is acting, from their session. Refuses if they aren't logged in:
        no session, or one that has been logged out."""
        acting = self._sessions.owner(database, actor) if actor is not None else None
        if acting is None:
            raise LoginRequired
        return acting

    def _disable(self, database, user_id: int) -> None:
        """Marks the user disabled and ends all their sessions."""
        self._users.disable(database, user_id)
        self._sessions.end_all_for(database, user_id)

    def log_in(self, username: str, password: str) -> Session:
        with self._engine.connect() as database:
            user = self._users.find(database, username)
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
            user = self._users.find(database, username)
        return user.public_id if user is not None else None

    def log_out(self, session: Session) -> None:
        with self._engine.begin() as database:
            user = self._sessions.owner(database, session)
            self._sessions.end(database, session)
        # A session that's already gone has nobody to name.
        if user is not None:
            _record("logged out", user.public_id)
