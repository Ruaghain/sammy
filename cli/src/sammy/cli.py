"""The `sammy` command."""

import argparse
import logging
import sys

from sammy.config import ConfigurationError, load_settings
from sammy.logs import configure_logging
from sammy.startup import start

_log = logging.getLogger("sammy")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sammy", description="Sammy, the household agent.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "migrate", help="create Sammy's database, or bring it up to date, then stop"
    )
    arguments = parser.parse_args(argv)

    try:
        settings = load_settings()
    except ConfigurationError as problem:
        print(f"sammy: {problem}", file=sys.stderr)
        return 2
    configure_logging(settings)

    if arguments.command == "migrate":
        sammy = start(settings)
        sammy.close()
        _log.info("database up to date", extra={"event": "database migrated"})
        print("Sammy's database is up to date.")
    return 0
