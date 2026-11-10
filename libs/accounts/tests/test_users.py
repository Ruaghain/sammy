import uuid

from alembic import command
from alembic.config import Config
from argon2 import PasswordHasher
from sqlalchemy import text

from sammy.accounts.schema import MIGRATIONS
from sammy.accounts import Session
from sammy.accounts.sessions import token_hash
from sammy.core import create_engine, migration_connection


def database_url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'sammy.sqlite'}"


def test_each_user_gets_their_own_uuid7_public_id(tmp_path, start_accounts):
    accounts_ = start_accounts(database_url(tmp_path))
    accounts_.create_user("test.user", "correct-horse")
    accounts_.create_user("test.other", "battery-staple")

    first, second = accounts_.public_id("test.user"), accounts_.public_id("test.other")

    assert isinstance(first, uuid.UUID) and first.version == 7
    assert isinstance(second, uuid.UUID) and second.version == 7
    assert first != second


def test_an_unknown_username_has_no_public_id(tmp_path, start_accounts):
    assert start_accounts(database_url(tmp_path)).public_id("unknown.user") is None


def test_a_public_id_never_changes(tmp_path, start_accounts):
    start_accounts(database_url(tmp_path)).create_user("test.user", "correct-horse")
    before = start_accounts(database_url(tmp_path)).public_id("test.user")

    after = start_accounts(database_url(tmp_path)).public_id("test.user")

    assert after == before


def test_upgrading_from_0001_keeps_users_and_their_sessions(tmp_path, start_accounts):
    # Several users, each with a session, with usernames sorting either side
    # of each other, so a session copied to the wrong user (or to several)
    # shows.
    url = database_url(tmp_path)
    usernames = ["test.alpha", "test.middle", "test.zulu"]
    tokens = {username: f"an-existing-session-token-for-{username}" for username in usernames}
    engine = create_engine(url)
    with migration_connection(engine) as connection:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        # Users and live sessions, as the 0001 code stored them.
        for username in usernames:
            connection.execute(
                text("INSERT INTO users (username, password_hash) VALUES (:u, :h)"),
                {"u": username, "h": PasswordHasher().hash("correct-horse")},
            )
            connection.execute(
                text("INSERT INTO sessions (token_hash, username) VALUES (:t, :u)"),
                {"t": token_hash(Session(tokens[username])), "u": username},
            )
    engine.dispose()

    upgraded = start_accounts(url)  # migrates 0001 -> head

    for username in usernames:
        assert upgraded.user_for(Session(tokens[username])) == username
        assert upgraded.public_id(username).version == 7
        upgraded.log_in(username, "correct-horse")


def test_downgrading_to_0001_keeps_users_and_their_sessions(tmp_path, start_accounts):
    # Every user has a session, so a session copied to the wrong user (or to
    # several, e.g. every user created after its own) shows.
    url = database_url(tmp_path)
    accounts_ = start_accounts(url)  # at head
    usernames = ["test.first", "test.second", "test.third"]
    for username in usernames:
        accounts_.create_user(username, "correct-horse")
    sessions = {username: accounts_.log_in(username, "correct-horse") for username in usernames}

    engine = create_engine(url)
    with migration_connection(engine) as connection:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.attributes["connection"] = connection
        command.downgrade(config, "0001")
        stored_sessions = connection.execute(text("SELECT token_hash, username FROM sessions")).all()
        users = connection.execute(text("SELECT username FROM users ORDER BY username")).all()
    engine.dispose()

    assert sorted(stored_sessions) == sorted(
        (token_hash(session), username) for username, session in sessions.items()
    )
    assert users == [(username,) for username in sorted(usernames)]
