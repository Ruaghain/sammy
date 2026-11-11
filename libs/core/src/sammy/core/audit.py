"""Logging what happens in Sammy: who did what, to whom.

Logs name users only by public_id: never by username, and never with a
password or session token (see CLAUDE.md, Logging). Every entry also carries
its event and ids as fields, so they can be found without parsing the
message.
"""

import logging
import uuid


class AuditLog:
    """One package's record of events. Each package has one, named after the
    package rather than a module (e.g. "accounts"), so its log lines read the
    same wherever in the package they come from."""

    def __init__(self, name: str):
        self._log = logging.getLogger(name)

    def record(
        self,
        event: str,
        public_id: uuid.UUID | None = None,
        level: int = logging.INFO,
        actor_public_id: uuid.UUID | None = None,
        **details: str,
    ) -> None:
        """Logs an event: about a user (`public_id`) if it concerns one, who
        did it if someone else did, and any details (e.g. role, permission)."""
        fields = {"event": event}
        message, args = "%s:", [event]
        if public_id is not None:
            fields["public_id"] = str(public_id)
            message, args = message + " user %s", [*args, public_id]
        for name, value in details.items():
            fields[name] = value
            message, args = message + f" {name} %s", [*args, value]
        if actor_public_id is not None:
            fields["actor_public_id"] = str(actor_public_id)
            message, args = message + " by user %s", [*args, actor_public_id]
        self._log.log(level, message, *args, extra=fields)

    def record_about_nobody(self, event: str, message: str, level: int = logging.INFO) -> None:
        """Logs an event that names no user, e.g. a login for an unknown
        username, whose username must never be logged."""
        self._log.log(level, message, extra={"event": event})
