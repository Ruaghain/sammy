"""Sammy's users, roles and login. AccountService is the way in; see
service.py. Run migrate(engine) at startup, before creating it. The modules
alongside it each hold one concern."""

from sammy.accounts.errors import (
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
from sammy.accounts.schema import migrate
from sammy.accounts.service import AccountService
from sammy.accounts.sessions import Session

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
