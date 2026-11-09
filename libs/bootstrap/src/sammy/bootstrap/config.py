"""Sammy's settings, read from the environment (and a local .env file).

See CLAUDE.md, Model configuration and Logging. A real environment variable
always wins over the same name in .env.
"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


class ConfigurationError(Exception):
    """Raised when Sammy can't start because a setting is missing or invalid.
    The message says which setting and what it should look like, and never
    includes a setting's value: a database URL can contain a password."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_dir: Path
    log_level: int
    log_retention_days: int


def load_settings(
    environ: Mapping[str, str] | None = None, env_file: Path = Path(".env")
) -> Settings:
    found = {name: value for name, value in dotenv_values(env_file).items() if value is not None}
    found.update(os.environ if environ is None else environ)

    database_url = found.get("SAMMY_DATABASE_URL", "").strip()
    if not database_url:
        raise ConfigurationError(
            "SAMMY_DATABASE_URL is not set. Point it at Sammy's database, e.g. "
            "sqlite:///sammy.sqlite or postgresql+psycopg://user:password@host/sammy"
        )

    level_name = found.get("SAMMY_LOG_LEVEL", "INFO").strip().upper()
    log_level = logging.getLevelNamesMapping().get(level_name)
    if log_level is None:
        raise ConfigurationError(
            "SAMMY_LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR or CRITICAL"
        )

    retention = found.get("SAMMY_LOG_RETENTION_DAYS", "30").strip()
    if not retention.isdigit() or int(retention) < 1:
        raise ConfigurationError("SAMMY_LOG_RETENTION_DAYS must be a whole number of days, 1 or more")

    return Settings(
        database_url=database_url,
        log_dir=Path(found.get("SAMMY_LOG_DIR", "logs")),
        log_level=log_level,
        log_retention_days=int(retention),
    )
