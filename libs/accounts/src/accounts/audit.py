"""Logging what happens to accounts.

Logs name users only by public_id: never by username, and never with a
password or session token (see CLAUDE.md, Logging). Every entry also carries
its event and ids as fields, so they can be found without parsing the
message.
"""

import logging
import uuid

# Named "accounts" rather than after this module, so log lines read the same
# wherever in the package they come from.
_log = logging.getLogger("accounts")


def record(
    event: str,
    public_id: uuid.UUID,
    level: int = logging.INFO,
    actor_public_id: uuid.UUID | None = None,
    **details: str,
) -> None:
    """Logs an event about a user, who did it if someone else did, and any
    details (e.g. role, permission)."""
    fields = {"event": event, "public_id": str(public_id)}
    message, args = "%s: user %s", [event, public_id]
    for name, value in details.items():
        fields[name] = value
        message, args = message + f" {name} %s", [*args, value]
    if actor_public_id is not None:
        fields["actor_public_id"] = str(actor_public_id)
        message, args = message + " by user %s", [*args, actor_public_id]
    _log.log(level, message, *args, extra=fields)


def record_about_nobody(event: str, message: str, level: int = logging.INFO) -> None:
    """Logs an event that names no user, e.g. a login for an unknown username,
    whose username must never be logged."""
    _log.log(level, message, extra={"event": event})
