import pytest
from argon2 import PasswordHasher

from accounts import Accounts, LoginRefused


@pytest.fixture
def password_checks(monkeypatch) -> list[str]:
    """Records the hash each password check is made against."""
    checked: list[str] = []
    real_verify = PasswordHasher.verify

    def recording_verify(self, hash, password):
        checked.append(hash)
        return real_verify(self, hash, password)

    monkeypatch.setattr(PasswordHasher, "verify", recording_verify)
    return checked


def test_an_unknown_user_still_costs_a_full_password_check(tmp_path, password_checks):
    accounts = Accounts(f"sqlite:///{tmp_path / 'sammy.sqlite'}")

    with pytest.raises(LoginRefused):
        accounts.log_in("unknown.user", "correct-horse")

    assert len(password_checks) == 1
    assert password_checks[0].startswith("$argon2id$")
