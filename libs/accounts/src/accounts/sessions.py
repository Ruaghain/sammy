"""Sessions: proof that someone has logged in.

SessionService only works inside a connection it's given and never opens a
transaction, so the caller can combine session changes with others.
"""

import secrets
from dataclasses import dataclass, field
from hashlib import sha256

from sqlalchemy import Connection, Row, delete, insert, select

from accounts.tables import sessions, users


@dataclass(frozen=True)
class Session:
    """Proof of a login, held by whoever logged in. The token is a secret, so
    it is kept out of the repr and never ends up in logs by accident."""

    token: str = field(repr=False)


class SessionService:
    def start(self, database: Connection, user_id: int) -> Session:
        """A new session for this user. Only a hash of its token is stored."""
        session = Session(secrets.token_urlsafe(32))
        database.execute(insert(sessions).values(token_hash=token_hash(session), user_id=user_id))
        return session

    def owner(self, database: Connection, session: Session) -> Row | None:
        """The user a session belongs to (their id, username and public_id), or
        None if the session doesn't exist, e.g. because it has been logged out."""
        return database.execute(
            select(users.c.id, users.c.username, users.c.public_id)
            .join(sessions, sessions.c.user_id == users.c.id)
            .where(sessions.c.token_hash == token_hash(session))
        ).one_or_none()

    def end(self, database: Connection, session: Session) -> None:
        """Ends one session. Ending one that's already gone does nothing."""
        database.execute(delete(sessions).where(sessions.c.token_hash == token_hash(session)))

    def end_all_for(self, database: Connection, user_id: int) -> None:
        """Ends every session this user has, wherever they're logged in."""
        database.execute(delete(sessions).where(sessions.c.user_id == user_id))


def token_hash(session: Session) -> str:
    # Session tokens are long and random, so a plain SHA-256 is enough; unlike
    # passwords they don't need a slow, salted hash. Only the hash is stored,
    # so a copy of the database can't be used to take over a session.
    return sha256(session.token.encode()).hexdigest()
