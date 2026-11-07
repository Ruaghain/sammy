"""Roles and permissions: which roles exist, who holds them, and what they
allow.

Permissions are fixed in code (see CLAUDE.md, Stored data); the built-in
admin role has every one of them. RoleService only works inside a connection
it's given and never opens a transaction, so the caller can combine role
changes with others.
"""

from sqlalchemy import Connection, delete, insert, select

from accounts.tables import ADMIN_ROLE, roles, user_roles

MANAGE_USERS = "manage users"
MANAGE_ROLES = "manage roles"


class RoleService:
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
