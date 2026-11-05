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
    {"username": "test.user", "password": ""},
    {"username": "test.user", "password": "battery-staple"},
)
@scenario("user-login.feature", "Login is refused without revealing which detail was wrong")
def test_login_is_refused_without_revealing_which_detail_was_wrong():
    pass


@scenario("user-login.feature", "Talking to Sammy requires logging in")
def test_talking_to_sammy_requires_logging_in():
    pass


@given(parsers.parse('a user "{username}" with the password "{password}"'))
def a_user_with_the_password(sammy: SammyDriver, username: str, password: str):
    sammy.add_user(username, password)


# A regex rather than parsers.parse, whose "{password}" can't match an empty
# password.
@given("I am not logged in")
def given_i_am_not_logged_in(sammy: SammyDriver):
    sammy.ensure_logged_out()


@when("I send Sammy a message")
def i_send_sammy_a_message(sammy: SammyDriver):
    sammy.send_message("What's on the calendar today?")


@when(parsers.re(r'I log in as "(?P<username>[^"]+)" with the password "(?P<password>[^"]*)"'))
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


@then("I am asked to log in")
def i_am_asked_to_log_in(sammy: SammyDriver):
    assert sammy.was_asked_to_log_in()
