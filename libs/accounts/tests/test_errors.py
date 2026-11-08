import inspect

import accounts
from accounts import AccountsError, errors


def test_every_refusal_from_accounts_is_an_accounts_error():
    refusals = [
        value
        for value in vars(errors).values()
        if inspect.isclass(value)
        and issubclass(value, Exception)
        and value.__module__ == errors.__name__
        and value is not AccountsError
    ]

    assert len(refusals) == 10  # every refusal, LoginRequired included
    assert all(issubclass(refusal, AccountsError) for refusal in refusals)
    # ...and each is importable straight from accounts, as before.
    assert all(getattr(accounts, refusal.__name__) is refusal for refusal in refusals)
