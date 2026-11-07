import logging

import pytest
from sqlalchemy import create_engine, inspect

from sammy.cli import main


@pytest.fixture
def in_a_folder(tmp_path, monkeypatch):
    """Runs the command from an empty folder, with no settings in the
    environment, and puts the root logger back afterwards."""
    monkeypatch.chdir(tmp_path)
    for name in ("SAMMY_DATABASE_URL", "SAMMY_LOG_DIR", "SAMMY_LOG_LEVEL", "SAMMY_LOG_RETENTION_DAYS"):
        monkeypatch.delenv(name, raising=False)
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield tmp_path
    for handler in root.handlers[:]:
        if handler not in handlers:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(level)


def test_migrate_creates_the_database_and_logs_it(in_a_folder, monkeypatch, capsys):
    monkeypatch.setenv("SAMMY_DATABASE_URL", f"sqlite:///{in_a_folder / 'sammy.sqlite'}")

    assert main(["migrate"]) == 0

    tables = inspect(create_engine(f"sqlite:///{in_a_folder / 'sammy.sqlite'}")).get_table_names()
    assert {"users", "sessions", "roles", "user_roles"} <= set(tables)
    assert "up to date" in capsys.readouterr().out
    assert "database up to date" in (in_a_folder / "logs" / "sammy.log").read_text()


def test_refuses_to_start_without_a_database(in_a_folder, capsys):
    assert main(["migrate"]) == 2

    assert "SAMMY_DATABASE_URL is not set" in capsys.readouterr().err
    assert not (in_a_folder / "logs").exists()


def test_never_logs_or_prints_the_database_url(in_a_folder, monkeypatch, capsys):
    url = f"sqlite:///{in_a_folder / 'sammy.sqlite'}"
    monkeypatch.setenv("SAMMY_DATABASE_URL", url)

    main(["migrate"])

    output = capsys.readouterr()
    assert url not in output.out + output.err
    assert url not in (in_a_folder / "logs" / "sammy.log").read_text()
