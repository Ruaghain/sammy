"""Steps shared by more than one feature. Steps used by a single feature live
in that feature's test_<name>.py."""

from pytest_bdd import given, parsers, when

from drivers.sammy import SammyDriver


@given(parsers.parse('a user "{username}" with the password "{password}"'))
def a_user_with_the_password(sammy: SammyDriver, username: str, password: str):
    sammy.add_user(username, password)


# A regex rather than parsers.parse, whose "{password}" can't match an empty
# password.
@when(parsers.re(r'I log in as "(?P<username>[^"]+)" with the password "(?P<password>[^"]*)"'))
def i_log_in(sammy: SammyDriver, username: str, password: str):
    sammy.log_in(username, password)
