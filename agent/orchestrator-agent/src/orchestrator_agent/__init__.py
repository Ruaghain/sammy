from accounts import Session


class LoginRequired(Exception):
    """Raised when someone who isn't logged in tries to talk to Sammy."""


class Orchestrator:
    def handle(self, session: Session | None, message: str) -> None:
        if session is None:
            raise LoginRequired
        # No scenario yet says what Sammy does with a logged-in user's message.
        raise NotImplementedError("Routing to agents isn't built yet")
