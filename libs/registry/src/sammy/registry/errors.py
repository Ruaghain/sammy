"""Everything the registry can refuse with. Each is part of the public API."""


class RegistryError(Exception):
    """Base of every refusal from the registry, so a caller (e.g. the web
    front end) can handle them all in one place. Refusals about who is acting
    (not logged in, not allowed) come from accounts."""


class AgentShortNameTaken(RegistryError):
    """Raised when adding an agent whose short name is already in use."""


class AgentNameTaken(RegistryError):
    """Raised when adding an agent whose name another agent already has."""


class InvalidShortName(RegistryError):
    """Raised when adding an agent whose short name isn't capital letters,
    digits and underscores, starting with a letter."""
