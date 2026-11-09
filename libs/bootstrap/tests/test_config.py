import logging

import pytest

from sammy.bootstrap.config import ConfigurationError, load_settings

DATABASE = "sqlite:///sammy.sqlite"


def test_reads_settings_from_the_environment(tmp_path):
    settings = load_settings(
        {
            "SAMMY_DATABASE_URL": DATABASE,
            "SAMMY_LOG_DIR": "/var/log/sammy",
            "SAMMY_LOG_LEVEL": "debug",
            "SAMMY_LOG_RETENTION_DAYS": "7",
        },
        env_file=tmp_path / "missing.env",
    )

    assert settings.database_url == DATABASE
    assert str(settings.log_dir) == "/var/log/sammy"
    assert settings.log_level == logging.DEBUG
    assert settings.log_retention_days == 7


def test_logging_defaults(tmp_path):
    settings = load_settings({"SAMMY_DATABASE_URL": DATABASE}, env_file=tmp_path / "missing.env")

    assert str(settings.log_dir) == "logs"
    assert settings.log_level == logging.INFO
    assert settings.log_retention_days == 30


def test_reads_a_local_env_file_and_the_environment_wins(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SAMMY_DATABASE_URL=sqlite:///from-env-file.sqlite\nSAMMY_LOG_LEVEL=WARNING\n")

    settings = load_settings({"SAMMY_LOG_LEVEL": "ERROR"}, env_file=env_file)

    assert settings.database_url == "sqlite:///from-env-file.sqlite"
    assert settings.log_level == logging.ERROR


@pytest.mark.parametrize(
    "environ, setting",
    [
        ({}, "SAMMY_DATABASE_URL"),
        ({"SAMMY_DATABASE_URL": "  "}, "SAMMY_DATABASE_URL"),
        ({"SAMMY_DATABASE_URL": DATABASE, "SAMMY_LOG_LEVEL": "LOUD"}, "SAMMY_LOG_LEVEL"),
        ({"SAMMY_DATABASE_URL": DATABASE, "SAMMY_LOG_RETENTION_DAYS": "a week"}, "SAMMY_LOG_RETENTION_DAYS"),
        ({"SAMMY_DATABASE_URL": DATABASE, "SAMMY_LOG_RETENTION_DAYS": "0"}, "SAMMY_LOG_RETENTION_DAYS"),
    ],
)
def test_refuses_a_missing_or_invalid_setting_and_names_it(tmp_path, environ, setting):
    with pytest.raises(ConfigurationError, match=setting):
        load_settings(environ, env_file=tmp_path / "missing.env")


def test_a_refusal_never_shows_a_setting_s_value(tmp_path):
    secret_url = "postgresql+psycopg://sammy:not-a-real-password@db.example/sammy"
    with pytest.raises(ConfigurationError) as refusal:
        load_settings(
            {"SAMMY_DATABASE_URL": secret_url, "SAMMY_LOG_LEVEL": "LOUD"},
            env_file=tmp_path / "missing.env",
        )

    assert "not-a-real-password" not in str(refusal.value)
