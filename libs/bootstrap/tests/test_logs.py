import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import pytest

from sammy.bootstrap.config import Settings
from sammy.bootstrap.logs import configure_logging


@pytest.fixture
def configured(tmp_path):
    root = logging.getLogger()
    previous_level = root.level
    settings = Settings(
        database_url="sqlite://",
        log_dir=tmp_path / "logs",
        log_level=logging.WARNING,
        log_retention_days=12,
    )
    handler = configure_logging(settings)
    yield settings, handler
    root.removeHandler(handler)
    handler.close()
    root.setLevel(previous_level)


def test_one_file_in_the_log_folder_rotated_at_midnight_utc(configured):
    settings, handler = configured

    assert isinstance(handler, TimedRotatingFileHandler)
    assert Path(handler.baseFilename) == (settings.log_dir / "sammy.log").resolve()
    assert handler.when == "MIDNIGHT"
    assert handler.utc is True
    assert handler.backupCount == 12


def test_only_records_at_or_above_the_configured_level(configured):
    settings, handler = configured

    logging.getLogger("test.logs").info("not written")
    logging.getLogger("test.logs").warning("written")
    handler.flush()

    contents = (settings.log_dir / "sammy.log").read_text()
    assert "written" in contents
    assert "not written" not in contents


def test_timestamps_are_utc(configured):
    settings, handler = configured

    logging.getLogger("test.logs").warning("a line")
    handler.flush()

    line = (settings.log_dir / "sammy.log").read_text().splitlines()[-1]
    assert line.split(" ", 1)[0].endswith("Z")
