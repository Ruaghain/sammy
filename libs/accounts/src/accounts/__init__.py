"""Sammy's users, roles and login. AccountService is the way in; see
service.py. The modules alongside it each hold one concern."""

from accounts.errors import (
    AccountsError,
    LastManagerRequired,
    LoginRefused,
    LoginRequired,
    PermissionDenied,
    RoleAlreadyHeld,
    SetupAlreadyDone,
    UnknownRole,
    UsernameTaken,
)
from accounts.service import AccountService
from accounts.sessions import Session

__all__ = [
    "AccountService",
    "AccountsError",
    "LastManagerRequired",
    "LoginRefused",
    "LoginRequired",
    "PermissionDenied",
    "RoleAlreadyHeld",
    "Session",
    "SetupAlreadyDone",
    "UnknownRole",
    "UsernameTaken",
]
