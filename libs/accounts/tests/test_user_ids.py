import uuid

from alembic import command
from alembic.config import Config
from argon2 import PasswordHasher
from sqlalchemy import create_engine, text

import accounts
from accounts import Accounts, Session
from accounts.sessions import token_hash


def database_url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'sammy.sqlite'}"


def test_each_user_gets_their_own_uuid7_public_id(tmp_path):
    accounts_ = Accounts(database_url(tmp_path))
    accounts_.create_user("test.user", "correct-horse")
    accounts_.create_user("test.other", "battery-staple")

    first, second = accounts_.public_id("test.user"), accounts_.public_id("test.other")

    assert isinstance(first, uuid.UUID) and first.version == 7
    assert isinstance(second, uuid.UUID) and second.version == 7
    assert first != second


def test_an_unknown_username_has_no_public_id(tmp_path):
    assert Accounts(database_url(tmp_path)).public_id("unknown.user") is None


def test_a_public_id_never_changes(tmp_path):
    Accounts(database_url(tmp_path)).create_user("test.user", "correct-horse")
    before = Accounts(database_url(tmp_path)).public_id("test.user")

    after = Accounts(database_url(tmp_path)).public_id("test.user")

    assert after == before


def test_upgrading_from_0001_keeps_users_and_their_sessions(tmp_path):
    url = database_url(tmp_path)
    token = "an-existing-session-token"
    engine = create_engine(url)
    with engine.begin() as connection:
        config = Config()
        config.set_main_option("script_location", str(accounts._MIGRATIONS))
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        # A user and a live session, as the 0001 code stored them.
        connection.execute(
            text("INSERT INTO users (username, password_hash) VALUES (:u, :h)"),
            {"u": "test.user", "h": PasswordHasher().hash("correct-horse")},
        )
        connection.execute(
            text("INSERT INTO sessions (token_hash, username) VALUES (:t, :u)"),
            {"t": token_hash(Session(token)), "u": "test.user"},
        )
    engine.dispose()

    upgraded = Accounts(url)  # applies 0002

    assert upgraded.user_for(Session(token)) == "test.user"
    assert upgraded.public_id("test.user").version == 7
    upgraded.log_in("test.user", "correct-horse")


def test_downgrading_to_0001_keeps_users_and_their_sessions(tmp_path):
    url = database_url(tmp_path)
    accounts_ = Accounts(url)  # at head
    accounts_.create_user("test.other", "battery-staple")
    accounts_.create_user("test.user", "correct-horse")
    session = accounts_.log_in("test.user", "correct-horse")
    accounts_._engine.dispose()

    engine = create_engine(url)
    with engine.begin() as connection:
        config = Config()
        config.set_main_option("script_location", str(accounts._MIGRATIONS))
        config.attributes["connection"] = connection
        command.downgrade(config, "0001")
        sessions = connection.execute(text("SELECT token_hash, username FROM sessions")).all()
        users = connection.execute(text("SELECT username FROM users ORDER BY username")).all()
    engine.dispose()

    assert sessions == [(token_hash(session), "test.user")]
    assert users == [("test.other",), ("test.user",)]
