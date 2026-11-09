"""Sammy's log file: one sammy.log, rotated at midnight UTC (see CLAUDE.md,
Logging). Only the entry point calls this; library code just gets loggers."""

import logging
import time
from logging.handlers import TimedRotatingFileHandler

from sammy.bootstrap.config import Settings

LOG_FILE = "sammy.log"


def configure_logging(settings: Settings) -> logging.Handler:
    """Sends every log record at or above the configured level to the log
    file. Old files (sammy.log.<date>) are kept for the retention period,
    then deleted. Returns the handler, so a caller can remove it again."""
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        settings.log_dir / LOG_FILE,
        when="midnight",
        utc=True,
        backupCount=settings.log_retention_days,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(settings.log_level)
    return handler
