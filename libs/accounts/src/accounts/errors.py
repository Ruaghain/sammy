"""Everything accounts can refuse with. Each is part of the public API."""


class AccountsError(Exception):
    """Base of every refusal from accounts, so a caller (e.g. the web front
    end) can handle them all in one place."""


class LoginRefused(AccountsError):
    """Raised for every failed login, whatever the reason, so the refusal
    reveals nothing about which detail was wrong."""


class SetupAlreadyDone(AccountsError):
    """Raised when setup is run on a Sammy that already has users."""


class UsernameTaken(AccountsError):
    """Raised when creating a user whose username is already in use."""


class UnknownRole(AccountsError):
    """Raised when a role is named that doesn't exist."""


class LoginRequired(AccountsError):
    """Raised when someone who isn't logged in tries something that needs it,
    such as talking to Sammy or managing users."""


class PermissionDenied(AccountsError):
    """Raised when someone tries something none of their roles allows."""


class LastManagerRequired(AccountsError):
    """Raised when a change would leave no active user able to manage both
    users and roles."""


class RoleAlreadyHeld(AccountsError):
    """Raised when giving someone a role they already hold."""
