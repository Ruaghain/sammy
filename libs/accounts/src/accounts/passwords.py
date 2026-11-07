"""Password hashing: Argon2id, with a random salt per hash. The salt and
parameters are stored inside the hash string itself."""

import secrets
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def check_password(password_hash: str, password: str) -> bool:
    """Whether the password matches the hash. Always does the full, slow
    check, whatever the answer."""
    try:
        _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    return True


@cache
def unknown_user_hash() -> str:
    """The hash of a random password nobody knows, made with the same
    parameters as real ones. Checking a login for an unknown username
    against it takes as long as checking a wrong password, so the response
    time doesn't reveal which usernames exist."""
    return _hasher.hash(secrets.token_urlsafe(32))
