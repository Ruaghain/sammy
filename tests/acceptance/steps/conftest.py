"""Steps shared by more than one feature. Steps used by a single feature live
in that feature's test_<name>.py."""

from pytest_bdd import given, parsers, then, when

from drivers.sammy import SammyDriver


@given(parsers.parse('a user "{username}" with the password "{password}"'))
def a_user_with_the_password(sammy: SammyDriver, username: str, password: str):
    sammy.add_user(username, password)


# A regex rather than parsers.parse, whose "{password}" can't match an empty
# password.
@when(parsers.re(r'I log in as "(?P<username>[^"]+)" with the password "(?P<password>[^"]*)"'))
def i_log_in(sammy: SammyDriver, username: str, password: str):
    sammy.log_in(username, password)


@given("I am not logged in")
def given_i_am_not_logged_in(sammy: SammyDriver):
    sammy.ensure_logged_out()


@then("I am asked to log in")
def i_am_asked_to_log_in(sammy: SammyDriver):
    assert sammy.was_asked_to_log_in()


@then("I am not logged in")
def i_am_not_logged_in(sammy: SammyDriver):
    assert sammy.logged_in_user() is None


@then("I am told my username or password is incorrect")
def i_am_told_my_username_or_password_is_incorrect(sammy: SammyDriver):
    assert sammy.login_was_refused()


@then(parsers.parse('Sammy has recorded that a login as "{username}" was refused'))
def sammy_has_recorded_a_refused_login(sammy: SammyDriver, username: str):
    assert sammy.has_recorded("login refused", username)


@then(parsers.parse('"{username}" is still logged in'))
def is_still_logged_in(sammy: SammyDriver, username: str):
    assert sammy.is_logged_in(username)


@given(parsers.parse('I am logged in as the admin "{username}"'))
def i_am_logged_in_as_the_admin(sammy: SammyDriver, username: str):
    sammy.run_setup(username, "correct-horse")
    sammy.log_in(username, "correct-horse")


@when(parsers.parse('I give "{username}" the "{role}" role'))
def i_give_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.give_role(username, role)


@then(parsers.parse('"{username}" can create users'))
def can_create_users(sammy: SammyDriver, username: str):
    assert sammy.can_create_users(username)


@then(parsers.parse('"{username}" has no roles'))
def has_no_roles(sammy: SammyDriver, username: str):
    assert sammy.roles_of(username) == set()


@given(parsers.parse('"{username}" is logged in with the "{role}" role'))
def is_logged_in_with_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.someone_logs_in(username)
    sammy.give_role(username, role)


@given(parsers.parse('"{username}" has been given the "{role}" role'))
def has_been_given_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.give_role(username, role)
    assert role in sammy.roles_of(username)


@then(parsers.parse('I am logged in as "{username}"'))
def i_am_logged_in_as(sammy: SammyDriver, username: str):
    assert sammy.logged_in_user() == username


@then(parsers.parse('"{username}" can no longer create users'))
def can_no_longer_create_users(sammy: SammyDriver, username: str):
    assert not sammy.can_create_users(username)


@then(parsers.parse('"{username}" can still create users'))
def can_still_create_users(sammy: SammyDriver, username: str):
    assert sammy.can_create_users(username)


@given(parsers.parse('a user "{username}" with the "{role}" role'))
def a_user_with_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.add_user(username, "correct-horse")
    sammy.has_been_given_role(username, role)
