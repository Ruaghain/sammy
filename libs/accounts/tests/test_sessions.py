import sqlite3

from accounts import AccountService


def logged_in(tmp_path):
    database_path = tmp_path / "sammy.sqlite"
    accounts = AccountService(f"sqlite:///{database_path}")
    accounts.create_user("test.user", "correct-horse")
    return database_path, accounts.log_in("test.user", "correct-horse")


def test_only_a_hash_of_the_session_token_is_stored(tmp_path):
    database_path, session = logged_in(tmp_path)

    with sqlite3.connect(database_path) as database:
        stored = [row[0] for row in database.execute("SELECT token_hash FROM sessions")]

    assert len(stored) == 1
    assert session.token not in stored[0]


def test_the_session_token_is_not_shown_when_a_session_is_printed(tmp_path):
    _, session = logged_in(tmp_path)

    assert session.token not in repr(session)
    assert session.token not in str(session)
