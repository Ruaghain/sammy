"""Users: who exists, how they log in, and whether they're disabled.

UserService only works inside a connection it's given and never opens a
transaction, so the caller can combine user changes with others.
"""

import uuid

from sqlalchemy import Connection, Row, false, insert, select, update

from accounts.passwords import hash_password
from accounts.tables import users


class UserService:
    def create(self, database: Connection, username: str, password: str) -> tuple[int, uuid.UUID]:
        """A new user, with only a salted hash of their password stored and a
        fresh public id. Returns their id and public id."""
        public_id = uuid.uuid7()
        user_id = database.execute(
            insert(users)
            .values(public_id=public_id, username=username, password_hash=hash_password(password))
            .returning(users.c.id)
        ).scalar_one()
        return user_id, public_id

    def find(self, database: Connection, username: str) -> Row | None:
        """The user with this username (id, public_id, username,
        password_hash, disabled), or None if there's no such user."""
        return database.execute(
            select(
                users.c.id,
                users.c.public_id,
                users.c.username,
                users.c.password_hash,
                users.c.disabled,
            ).where(users.c.username == username)
        ).one_or_none()

    def disable(self, database: Connection, user_id: int) -> None:
        """Marks the user disabled, so they can't log in. Ending their sessions
        is the caller's job."""
        database.execute(update(users).where(users.c.id == user_id).values(disabled=True))

    def any_exist(self, database: Connection) -> bool:
        return database.execute(select(users.c.id).limit(1)).first() is not None

    def active_ids(self, database: Connection) -> list[int]:
        """The ids of every user who isn't disabled."""
        return list(
            database.execute(select(users.c.id).where(users.c.disabled == false())).scalars()
        )
