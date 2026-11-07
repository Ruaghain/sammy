import pytest
from pytest_bdd import given, parsers, scenario, then, when

from drivers.sammy import SammyDriver


@scenario("user-management.feature", "Setup creates the first admin")
def test_setup_creates_the_first_admin():
    pass


@scenario("user-management.feature", "Setup is refused once a user exists")
def test_setup_is_refused_once_a_user_exists():
    pass


@scenario("user-management.feature", "A new user can log in and starts with no roles")
def test_a_new_user_can_log_in_and_starts_with_no_roles():
    pass


@scenario("user-management.feature", "An admin gives a user a role")
def test_an_admin_gives_a_user_a_role():
    pass


@scenario("user-management.feature", "A username can only be used once")
def test_a_username_can_only_be_used_once():
    pass


@scenario("user-management.feature", "A user can't be given a role that doesn't exist")
def test_a_user_cant_be_given_a_role_that_doesnt_exist():
    pass


@pytest.mark.built_examples(
    {
        "action": 'create the user "test.new" with the password "correct-horse"',
        "unchanged": 'the user "test.new" doesn\'t exist',
    },
    {
        "action": 'give "test.other" the "admin" role',
        "unchanged": '"test.other" has no roles',
    },
    {
        "action": 'disable "test.other"',
        "unchanged": 'I can log in as "test.other" with the password "correct-horse"',
    },
)
@scenario("user-management.feature", "Only users who can manage users can change them")
def test_only_users_who_can_manage_users_can_change_them():
    pass


@scenario("user-management.feature", "Managing users requires logging in")
def test_managing_users_requires_logging_in():
    pass


@scenario("user-management.feature", "Removing a role applies to a user who is already logged in")
def test_removing_a_role_applies_to_a_user_who_is_already_logged_in():
    pass


@scenario("user-management.feature", "The last user who can manage users keeps the admin role")
def test_the_last_user_who_can_manage_users_keeps_the_admin_role():
    pass


@scenario("user-management.feature", "The last user who can manage users can't be disabled")
def test_the_last_user_who_can_manage_users_cant_be_disabled():
    pass


@scenario("user-management.feature", "A disabled user is refused like any other failed login")
def test_a_disabled_user_is_refused_like_any_other_failed_login():
    pass


@scenario("user-management.feature", "Disabling a user ends their session")
def test_disabling_a_user_ends_their_session():
    pass


@scenario("user-management.feature", "A user can't be given a role they already hold")
def test_a_user_cant_be_given_a_role_they_already_hold():
    pass


@scenario("user-management.feature", "Giving a role affects only that user")
def test_giving_a_role_affects_only_that_user():
    pass


@scenario("user-management.feature", "Someone else being an admin doesn't let me manage users")
def test_someone_else_being_an_admin_doesnt_let_me_manage_users():
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


@given(parsers.parse('I am logged in as the admin "{username}"'))
def i_am_logged_in_as_the_admin(sammy: SammyDriver, username: str):
    sammy.run_setup(username, "correct-horse")
    sammy.log_in(username, "correct-horse")


@when(parsers.parse('I create the user "{username}" with the password "{password}"'))
def i_create_the_user(sammy: SammyDriver, username: str, password: str):
    sammy.create_user(username, password)


@then(parsers.parse('"{username}" has no roles'))
def has_no_roles(sammy: SammyDriver, username: str):
    assert sammy.roles_of(username) == set()


@then(parsers.parse('Sammy has recorded that "{actor}" created "{username}"'))
def sammy_has_recorded_that_someone_created_a_user(sammy: SammyDriver, actor: str, username: str):
    assert sammy.has_recorded("user created", username, by=actor)


@when(parsers.parse('I give "{username}" the "{role}" role'))
def i_give_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.give_role(username, role)


@then(parsers.parse('"{username}" can create users'))
def can_create_users(sammy: SammyDriver, username: str):
    assert sammy.can_create_users(username)


@then(parsers.parse('Sammy has recorded that "{actor}" gave "{username}" the "{role}" role'))
def sammy_has_recorded_that_someone_gave_a_role(sammy: SammyDriver, actor: str, username: str, role: str):
    assert sammy.has_recorded("role given", username, by=actor, role=role)


@then("I am told the username is already taken")
def i_am_told_the_username_is_already_taken(sammy: SammyDriver):
    assert sammy.username_was_taken()


@then("I am told the role doesn't exist")
def i_am_told_the_role_doesnt_exist(sammy: SammyDriver):
    assert sammy.role_was_unknown()


@given(parsers.parse('I am logged in as "{username}", who has no roles'))
def i_am_logged_in_as_someone_with_no_roles(sammy: SammyDriver, username: str):
    sammy.add_user(username, "correct-horse")
    sammy.log_in(username, "correct-horse")


@then("I am told I don't have permission")
def i_am_told_i_dont_have_permission(sammy: SammyDriver):
    assert sammy.permission_was_denied()


@then(parsers.parse('the user "{username}" doesn\'t exist'))
def the_user_doesnt_exist(sammy: SammyDriver, username: str):
    assert not sammy.user_exists(username)


@then(parsers.parse('Sammy has recorded that "{username}" was refused permission to {permission}'))
def sammy_has_recorded_a_refused_permission(sammy: SammyDriver, username: str, permission: str):
    assert sammy.has_recorded("permission refused", username, permission=permission)


@when(parsers.parse('I disable "{username}"'))
def i_disable(sammy: SammyDriver, username: str):
    sammy.disable(username)


@given(parsers.parse('"{username}" is logged in with the "{role}" role'))
def is_logged_in_with_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.someone_logs_in(username)
    sammy.give_role(username, role)


@when(parsers.parse('I remove the "{role}" role from "{username}"'))
def i_remove_the_role(sammy: SammyDriver, role: str, username: str):
    sammy.remove_role(username, role)


@then(parsers.parse('"{username}" can no longer create users'))
def can_no_longer_create_users(sammy: SammyDriver, username: str):
    assert not sammy.can_create_users(username)


@then(parsers.parse('Sammy has recorded that "{actor}" removed the "{role}" role from "{username}"'))
def sammy_has_recorded_that_someone_removed_a_role(sammy: SammyDriver, actor: str, role: str, username: str):
    assert sammy.has_recorded("role removed", username, by=actor, role=role)


@given(
    parsers.parse(
        'I am logged in as the admin "{username}", the only user who can manage users and roles'
    )
)
def i_am_logged_in_as_the_only_admin(sammy: SammyDriver, username: str):
    sammy.run_setup(username, "correct-horse")
    sammy.log_in(username, "correct-horse")
    # Setup only works on an empty Sammy, so this admin is the only user.
    assert sammy.user_count() == 1


@then("I am told at least one user must be able to manage users and roles")
def i_am_told_someone_must_manage(sammy: SammyDriver):
    assert sammy.last_manager_was_protected()


@then(parsers.parse('"{username}" can still log in'))
def can_still_log_in(sammy: SammyDriver, username: str):
    assert sammy.can_log_in_with_their_password(username)


@given(parsers.parse('"{username}" has been disabled'))
def has_been_disabled(sammy: SammyDriver, username: str):
    sammy.has_been_disabled(username)


@given(parsers.parse('"{username}" is logged in'))
def is_logged_in(sammy: SammyDriver, username: str):
    sammy.someone_logs_in(username)


@then(parsers.parse('"{username}" is no longer logged in'))
def is_no_longer_logged_in(sammy: SammyDriver, username: str):
    assert not sammy.is_logged_in(username)


@then(parsers.parse('Sammy has recorded that "{actor}" disabled "{username}"'))
def sammy_has_recorded_that_someone_disabled_a_user(sammy: SammyDriver, actor: str, username: str):
    assert sammy.has_recorded("user disabled", username, by=actor)


@given(parsers.parse('"{username}" has been given the "{role}" role'))
def has_been_given_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.give_role(username, role)
    assert role in sammy.roles_of(username)


@then(parsers.parse('I am told "{username}" already has the "{role}" role'))
def i_am_told_they_already_have_the_role(sammy: SammyDriver, username: str, role: str):
    assert sammy.role_was_already_held()


@given(parsers.parse('a user "{username}" with the "{role}" role'))
def a_user_with_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.add_user(username, "correct-horse")
    sammy.has_been_given_role(username, role)
