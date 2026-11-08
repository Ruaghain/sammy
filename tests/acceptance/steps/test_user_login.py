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


@scenario("user-login.feature", "Logging out")
def test_logging_out():
    pass


@scenario("user-login.feature", "Each user logs in as themselves")
def test_each_user_logs_in_as_themselves():
    pass


@scenario("user-login.feature", "Logging out leaves everyone else logged in")
def test_logging_out_leaves_everyone_else_logged_in():
    pass


@scenario("user-login.feature", "A successful login is recorded")
def test_a_successful_login_is_recorded():
    pass


@scenario("user-login.feature", "A refused login is recorded")
def test_a_refused_login_is_recorded():
    pass


@scenario("user-login.feature", "Logging out is recorded")
def test_logging_out_is_recorded():
    pass


@scenario("user-login.feature", "A refused login for an unknown username is recorded without it")
def test_a_refused_login_for_an_unknown_username_is_recorded_without_it():
    pass


@pytest.mark.built_examples(
    {"leaving": "test.user", "staying": "test.other"},
    {"leaving": "test.other", "staying": "test.user"},
)
@scenario("user-login.feature", "Logging out is recorded for the person who logged out")
def test_logging_out_is_recorded_for_the_person_who_logged_out():
    pass


@given(parsers.parse('I am logged in as "{username}"'))
def given_i_am_logged_in_as(sammy: SammyDriver, username: str):
    sammy.add_user(username, "correct-horse")
    sammy.log_in(username, "correct-horse")


@when("I log out")
def i_log_out(sammy: SammyDriver):
    sammy.log_out()


@then("I am asked to log in when I send Sammy a message")
def i_am_asked_to_log_in_when_i_send_sammy_a_message(sammy: SammyDriver):
    sammy.send_message("What's on the calendar today?")
    assert sammy.was_asked_to_log_in()


@when("I send Sammy a message")
def i_send_sammy_a_message(sammy: SammyDriver):
    sammy.send_message("What's on the calendar today?")


@given(parsers.parse('"{first}" and "{second}" are both logged in'))
def both_are_logged_in(sammy: SammyDriver, first: str, second: str):
    sammy.someone_logs_in(first)
    sammy.someone_logs_in(second)
    # The step says both are logged in, so confirm Sammy agrees, each as
    # themselves, before going on.
    assert sammy.is_logged_in(first)
    assert sammy.is_logged_in(second)


@when(parsers.parse('"{username}" logs out'))
def someone_logs_out(sammy: SammyDriver, username: str):
    sammy.someone_logs_out(username)


@then(parsers.parse('Sammy has recorded that "{username}" logged in'))
def sammy_has_recorded_a_login(sammy: SammyDriver, username: str):
    assert sammy.has_recorded("login succeeded", username)


@then(parsers.parse('Sammy has recorded that "{username}" logged out'))
def sammy_has_recorded_a_logout(sammy: SammyDriver, username: str):
    assert sammy.has_recorded("logged out", username)


@then("Sammy has recorded that a login was refused for an unknown user")
def sammy_has_recorded_a_refused_login_for_an_unknown_user(sammy: SammyDriver):
    assert sammy.has_recorded_about_nobody("login refused for unknown user")


@then(parsers.parse('nothing Sammy has logged contains "{text}"'))
def nothing_sammy_has_logged_contains(sammy: SammyDriver, text: str):
    assert text not in sammy.everything_logged()


@then(parsers.parse('Sammy has not recorded that "{username}" logged out'))
def sammy_has_not_recorded_a_logout(sammy: SammyDriver, username: str):
    assert not sammy.has_recorded("logged out", username)
