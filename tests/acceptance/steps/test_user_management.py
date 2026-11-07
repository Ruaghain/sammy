from pytest_bdd import given, parsers, scenario, then, when

from drivers.sammy import SammyDriver


@scenario("user-management.feature", "Setup creates the first admin")
def test_setup_creates_the_first_admin():
    pass


@scenario("user-management.feature", "Setup is refused once a user exists")
def test_setup_is_refused_once_a_user_exists():
    pass


@given("no users exist")
def no_users_exist(sammy: SammyDriver):
    assert sammy.user_count() == 0


@when(parsers.parse('I run setup with the username "{username}" and the password "{password}"'))
def i_run_setup(sammy: SammyDriver, username: str, password: str):
    sammy.run_setup(username, password)


@then(parsers.parse('I can log in as "{username}" with the password "{password}"'))
def i_can_log_in_as(sammy: SammyDriver, username: str, password: str):
    assert sammy.can_log_in(username, password)


@then(parsers.parse('"{username}" has the "{role}" role'))
def has_the_role(sammy: SammyDriver, username: str, role: str):
    assert role in sammy.roles_of(username)


@then(parsers.parse('Sammy has recorded that setup created the admin "{username}"'))
def sammy_has_recorded_that_setup_created_the_admin(sammy: SammyDriver, username: str):
    assert sammy.has_recorded("setup created admin", username)


@then("I am told setup has already been completed")
def i_am_told_setup_has_already_been_completed(sammy: SammyDriver):
    assert sammy.setup_was_refused()


@then(parsers.parse('I can\'t log in as "{username}" with the password "{password}"'))
def i_cant_log_in_as(sammy: SammyDriver, username: str, password: str):
    assert not sammy.can_log_in(username, password)


@then("Sammy has recorded that setup was refused")
def sammy_has_recorded_that_setup_was_refused(sammy: SammyDriver):
    assert sammy.has_recorded_about_nobody("setup refused")
