from pytest_bdd import given, parsers, scenario, then, when

from drivers.sammy import SammyDriver


@scenario("user-login.feature", "Logging in with valid details")
def test_logging_in_with_valid_details():
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
