import pytest
from pytest_bdd import given, parsers, scenario, then, when

from drivers.sammy import SammyDriver


@scenario("user-login.feature", "Logging in with valid details")
def test_logging_in_with_valid_details():
    pass


@pytest.mark.built_examples(
    {"username": "test.user", "password": "wrong-password"},
    {"username": "unknown.user", "password": "correct-horse"},
    {"username": "test.user", "password": "Correct-Horse"},
)
@scenario("user-login.feature", "Login is refused without revealing which detail was wrong")
def test_login_is_refused_without_revealing_which_detail_was_wrong():
    pass


@given(parsers.parse('a user "{username}" with the password "{password}"'))
def a_user_with_the_password(sammy: SammyDriver, username: str, password: str):
    sammy.add_user(username, password)


@when(parsers.parse('I log in as "{username}" with the password "{password}"'))
def i_log_in(sammy: SammyDriver, username: str, password: str):
    sammy.log_in(username, password)


@then(parsers.parse('I am logged in as "{username}"'))
def i_am_logged_in_as(sammy: SammyDriver, username: str):
    assert sammy.logged_in_user() == username


@then("I am not logged in")
def i_am_not_logged_in(sammy: SammyDriver):
    assert sammy.logged_in_user() is None


@then("I am told my username or password is incorrect")
def i_am_told_my_username_or_password_is_incorrect(sammy: SammyDriver):
    assert sammy.login_was_refused()
