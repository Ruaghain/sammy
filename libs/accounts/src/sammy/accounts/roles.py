"""Roles and permissions: which roles exist, who holds them, and what they
allow.

Permissions are fixed in code (see CLAUDE.md, Stored data); the built-in
admin role has every one of them. RoleService only works inside a connection
it's given and never opens a transaction, so the caller can combine role
changes with others.
"""

from collections.abc import Callable

from sqlalchemy import Connection, delete, insert, select

from sammy.accounts.tables import ADMIN_ROLE, role_permissions, roles, user_roles

MANAGE_USERS = "manage users"
MANAGE_ROLES = "manage roles"
VIEW_AGENTS = "view agents"
MANAGE_AGENTS = "manage agents"
# Talking to one agent: "use agent <SHORT_NAME>", one permission per agent.
USE_AGENT = "use agent "

PERMISSIONS = frozenset({MANAGE_USERS, MANAGE_ROLES, VIEW_AGENTS, MANAGE_AGENTS})


def is_permission(name: str, agent_exists: Callable[[str], bool]) -> bool:
    """Whether Sammy has this permission: one of the fixed ones, or "use agent
    <SHORT_NAME>" for an agent that exists."""
    return name in PERMISSIONS or (
        name.startswith(USE_AGENT) and agent_exists(name.removeprefix(USE_AGENT))
    )


class RoleService:
    def create(self, database: Connection, name: str, permissions: list[str]) -> int:
        """A new role granting these permissions. Returns its id."""
        role_id = database.execute(insert(roles).values(name=name).returning(roles.c.id)).scalar_one()
        for permission in permissions:
            self.grant(database, role_id, permission)
        return role_id

    def grant(self, database: Connection, role_id: int, permission: str) -> None:
        """Lets the role do this as well. Everyone holding it can, at once."""
        database.execute(insert(role_permissions).values(role_id=role_id, permission=permission))

    def revoke(self, database: Connection, role_id: int, permission: str) -> None:
        """Stops the role doing this. Everyone holding it loses it, at once."""
        database.execute(
            delete(role_permissions).where(
                role_permissions.c.role_id == role_id, role_permissions.c.permission == permission
            )
        )

    def find_id(self, database: Connection, name: str) -> int | None:
        """The id of the role with this name, or None if there's no such role."""
        return database.execute(select(roles.c.id).where(roles.c.name == name)).scalar_one_or_none()

    def give(self, database: Connection, user_id: int, role_id: int) -> None:
        """Gives the user the role. user_roles' primary key refuses a role the
        user already holds, with an IntegrityError."""
        database.execute(insert(user_roles).values(user_id=user_id, role_id=role_id))

    def remove(self, database: Connection, user_id: int, role_id: int) -> None:
        database.execute(
            delete(user_roles).where(
                user_roles.c.user_id == user_id, user_roles.c.role_id == role_id
            )
        )

    def delete(self, database: Connection, role_id: int) -> None:
        """Deletes the role and what it allowed. Nobody may hold it: callers
        check is_held first."""
        database.execute(delete(role_permissions).where(role_permissions.c.role_id == role_id))
        database.execute(delete(roles).where(roles.c.id == role_id))

    def permissions(self, database: Connection, role_id: int) -> set[str]:
        """What this role grants (the admin role grants everything without
        listing it)."""
        return set(
            database.execute(
                select(role_permissions.c.permission).where(role_permissions.c.role_id == role_id)
            ).scalars()
        )

    def is_held(self, database: Connection, role_id: int) -> bool:
        """Whether anyone holds this role."""
        return (
            database.execute(select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)).first()
            is not None
        )

    def is_granted(self, database: Connection, permission: str) -> bool:
        """Whether any role lists this permission. The admin role grants
        everything without listing it, so it never counts."""
        return (
            database.execute(
                select(role_permissions.c.role_id).where(role_permissions.c.permission == permission)
            ).first()
            is not None
        )

    def names_of(self, database: Connection, user_id: int) -> set[str]:
        """The names of the roles this user holds."""
        return set(
            database.execute(
                select(roles.c.name)
                .join(user_roles, user_roles.c.role_id == roles.c.id)
                .where(user_roles.c.user_id == user_id)
            ).scalars()
        )

    def can(self, database: Connection, user_id: int, permission: str) -> bool:
        """Whether any of the user's roles allows this: the admin role allows
        everything, any other role what its permissions say."""
        is_admin = database.execute(
            select(roles.c.id)
            .join(user_roles, user_roles.c.role_id == roles.c.id)
            .where(user_roles.c.user_id == user_id, roles.c.name == ADMIN_ROLE)
        ).first()
        granted = database.execute(
            select(role_permissions.c.role_id)
            .join(user_roles, user_roles.c.role_id == role_permissions.c.role_id)
            .where(user_roles.c.user_id == user_id, role_permissions.c.permission == permission)
        ).first()
        return is_admin is not None or granted is not None

    def someone_can_manage(
        self, database: Connection, active_ids: list[int], excluding: int | None = None
    ) -> bool:
        """Whether at least one of the active users, other than `excluding`,
        can still manage both users and roles, so Sammy can never be locked out
        of its own administration. Disabled users can't log in, so the caller
        passes only active users."""
        return any(
            self.can(database, user_id, MANAGE_USERS) and self.can(database, user_id, MANAGE_ROLES)
            for user_id in active_ids
            if user_id != excluding
        )
