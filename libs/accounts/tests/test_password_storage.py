import sqlite3

from accounts import Accounts


def stored_password_hashes(database_path) -> dict[str, str]:
    with sqlite3.connect(database_path) as database:
        return dict(database.execute("SELECT username, password_hash FROM users"))


def test_stores_an_argon2id_hash_never_the_password(tmp_path):
    database_path = tmp_path / "sammy.sqlite"
    accounts = Accounts(f"sqlite:///{database_path}")

    accounts.create_user("test.user", "correct-horse")

    stored = stored_password_hashes(database_path)["test.user"]
    assert stored.startswith("$argon2id$")
    assert "correct-horse" not in stored


def test_the_same_password_is_salted_differently_for_each_user(tmp_path):
    database_path = tmp_path / "sammy.sqlite"
    accounts = Accounts(f"sqlite:///{database_path}")

    accounts.create_user("test.user", "correct-horse")
    accounts.create_user("test.other", "correct-horse")

    stored = stored_password_hashes(database_path)
    assert stored["test.user"] != stored["test.other"]
