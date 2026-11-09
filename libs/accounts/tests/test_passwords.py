"""Password storage and the cost of checking one: what no scenario can see."""

import sqlite3

import pytest
from argon2 import PasswordHasher

from sammy.accounts import LoginRefused


def stored_password_hashes(database_path) -> dict[str, str]:
    with sqlite3.connect(database_path) as database:
        return dict(database.execute("SELECT username, password_hash FROM users"))


def test_stores_an_argon2id_hash_never_the_password(tmp_path, start_accounts):
    database_path = tmp_path / "sammy.sqlite"
    accounts = start_accounts(f"sqlite:///{database_path}")

    accounts.create_user("test.user", "correct-horse")

    stored = stored_password_hashes(database_path)["test.user"]
    assert stored.startswith("$argon2id$")
    assert "correct-horse" not in stored


def test_the_same_password_is_salted_differently_for_each_user(tmp_path, start_accounts):
    database_path = tmp_path / "sammy.sqlite"
    accounts = start_accounts(f"sqlite:///{database_path}")

    accounts.create_user("test.user", "correct-horse")
    accounts.create_user("test.other", "correct-horse")

    stored = stored_password_hashes(database_path)
    assert stored["test.user"] != stored["test.other"]

@pytest.fixture
def password_checks(monkeypatch) -> list[str]:
    """Records the hash each password check is made against."""
    checked: list[str] = []
    real_verify = PasswordHasher.verify

    def recording_verify(self, hash, password):
        checked.append(hash)
        return real_verify(self, hash, password)

    monkeypatch.setattr(PasswordHasher, "verify", recording_verify)
    return checked


def test_an_unknown_user_still_costs_a_full_password_check(tmp_path, password_checks, start_accounts):
    accounts = start_accounts(f"sqlite:///{tmp_path / 'sammy.sqlite'}")

    with pytest.raises(LoginRefused):
        accounts.log_in("unknown.user", "correct-horse")

    assert len(password_checks) == 1
    assert password_checks[0].startswith("$argon2id$")


def test_an_unknown_user_costs_no_more_than_a_wrong_password(tmp_path, monkeypatch, start_accounts):
    """The stand-in hash is made once, not on every unknown-user login: making
    it each time would add a second slow Argon2 step, and the extra time
    would reveal which usernames exist."""
    accounts = start_accounts(f"sqlite:///{tmp_path / 'sammy.sqlite'}")
    with pytest.raises(LoginRefused):
        accounts.log_in("unknown.user", "correct-horse")  # the stand-in may be made here

    hashes_made: list[str] = []
    real_hash = PasswordHasher.hash

    def recording_hash(self, password, *args, **kwargs):
        hashes_made.append(password)
        return real_hash(self, password, *args, **kwargs)

    monkeypatch.setattr(PasswordHasher, "hash", recording_hash)
    with pytest.raises(LoginRefused):
        accounts.log_in("unknown.user", "correct-horse")

    assert hashes_made == []
