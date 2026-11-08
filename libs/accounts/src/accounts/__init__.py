"""Sammy's users, roles and login. AccountService is the way in; see
service.py. Run migrate(engine) at startup, before creating it. The modules
alongside it each hold one concern."""

from accounts.errors import (
    AccountsError,
    AdminRoleIsFixed,
    LastManagerRequired,
    LoginRefused,
    LoginRequired,
    PermissionDenied,
    RoleAlreadyHeld,
    RoleInUse,
    RoleNameTaken,
    SetupAlreadyDone,
    UnknownPermission,
    UnknownRole,
    UsernameTaken,
)
from accounts.schema import migrate
from accounts.service import AccountService
from accounts.sessions import Session

__all__ = [
    "AccountService",
    "AccountsError",
    "AdminRoleIsFixed",
    "LastManagerRequired",
    "LoginRefused",
    "LoginRequired",
    "PermissionDenied",
    "RoleAlreadyHeld",
    "RoleInUse",
    "RoleNameTaken",
    "Session",
    "SetupAlreadyDone",
    "UnknownPermission",
    "UnknownRole",
    "UsernameTaken",
    "migrate",
]
