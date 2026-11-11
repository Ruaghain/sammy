"""Everything the registry can refuse with. Each is part of the public API."""


class RegistryError(Exception):
    """Base of every refusal from the registry, so a caller (e.g. the web
    front end) can handle them all in one place. Refusals about who is acting
    (not logged in, not allowed) come from accounts."""
