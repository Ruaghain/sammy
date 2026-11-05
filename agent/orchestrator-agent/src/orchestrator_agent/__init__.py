from accounts import Accounts, Session


class LoginRequired(Exception):
    """Raised when someone who isn't logged in tries to talk to Sammy."""


class Orchestrator:
    def __init__(self, accounts: Accounts):
        self._accounts = accounts

    def handle(self, session: Session | None, message: str) -> None:
        # A logged-out session is refused the same as no session at all.
        if session is None or self._accounts.user_for(session) is None:
            raise LoginRequired
        # No scenario yet says what Sammy does with a logged-in user's message.
        raise NotImplementedError("Routing to agents isn't built yet")
