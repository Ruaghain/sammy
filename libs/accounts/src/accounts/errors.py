"""Everything accounts can refuse with. Each is part of the public API."""


class LoginRefused(Exception):
    """Raised for every failed login, whatever the reason, so the refusal
    reveals nothing about which detail was wrong."""


class SetupAlreadyDone(Exception):
    """Raised when setup is run on a Sammy that already has users."""


class UsernameTaken(Exception):
    """Raised when creating a user whose username is already in use."""


class UnknownRole(Exception):
    """Raised when a role is named that doesn't exist."""


class LoginRequired(Exception):
    """Raised when someone who isn't logged in tries something that needs it,
    such as talking to Sammy or managing users."""


class PermissionDenied(Exception):
    """Raised when someone tries something none of their roles allows."""


class LastManagerRequired(Exception):
    """Raised when a change would leave no active user able to manage both
    users and roles."""


class RoleAlreadyHeld(Exception):
    """Raised when giving someone a role they already hold."""
