import pytest
from pytest_bdd import given, parsers, scenario, then, when

from drivers.sammy import SammyDriver


@scenario("role-management.feature", "A role gives its permissions to the users who hold it")
def test_a_role_gives_its_permissions_to_the_users_who_hold_it():
    pass


@when(parsers.parse('I create the role "{role}" that can {permissions}'))
def i_create_the_role(sammy: SammyDriver, role: str, permissions: str):
    sammy.create_role(role, permissions)


@then(parsers.parse('"{username}" can\'t create roles'))
def cant_create_roles(sammy: SammyDriver, username: str):
    assert not sammy.can_create_roles(username)


@then(parsers.parse('Sammy has recorded that "{actor}" created the role "{role}"'))
def sammy_has_recorded_that_someone_created_a_role(sammy: SammyDriver, actor: str, role: str):
    assert sammy.has_recorded("role created", by=actor, role=role)


@scenario("role-management.feature", "A user's permissions come from all of their roles")
def test_a_users_permissions_come_from_all_of_their_roles():
    pass


@then(parsers.parse('"{username}" can create roles'))
def can_create_roles(sammy: SammyDriver, username: str):
    assert sammy.can_create_roles(username)


@scenario("role-management.feature", "A user with no roles can log in but can't manage anything")
def test_a_user_with_no_roles_can_log_in_but_cant_manage_anything():
    pass


@then(parsers.parse('"{username}" can\'t create users'))
def cant_create_users(sammy: SammyDriver, username: str):
    assert not sammy.can_create_users(username)


@scenario("role-management.feature", "Adding a permission to a role applies to users who are already logged in")
def test_adding_a_permission_to_a_role_applies_to_users_who_are_already_logged_in():
    pass


@given(parsers.parse('a role "{role}" with no permissions'))
def a_role_with_no_permissions(sammy: SammyDriver, role: str):
    sammy.has_role(role, "no permissions")


@when(parsers.parse('I let the role "{role}" {permissions}'))
def i_let_the_role(sammy: SammyDriver, role: str, permissions: str):
    sammy.grant(role, permissions)


@then(parsers.parse('Sammy has recorded that "{actor}" let the role "{role}" {permissions}'))
def sammy_has_recorded_a_granted_permission(sammy: SammyDriver, actor: str, role: str, permissions: str):
    assert sammy.has_recorded_for_each(permissions, "permission granted", by=actor, role=role)


@scenario("role-management.feature", "Removing a permission from a role applies to users who are already logged in")
def test_removing_a_permission_from_a_role_applies_to_users_who_are_already_logged_in():
    pass


@when(parsers.parse('I stop the role "{role}" from {permissions}'))
def i_stop_the_role_from(sammy: SammyDriver, role: str, permissions: str):
    sammy.revoke(role, permissions)


@then(parsers.parse('Sammy has recorded that "{actor}" stopped the role "{role}" from {permissions}'))
def sammy_has_recorded_a_revoked_permission(sammy: SammyDriver, actor: str, role: str, permissions: str):
    assert sammy.has_recorded_for_each(
        permissions, "permission revoked", by=actor, role=role, phrased_as="doing"
    )


@scenario("role-management.feature", "The admin role can't be changed")
def test_the_admin_role_cant_be_changed():
    pass


@then("I am told the admin role can't be changed")
def i_am_told_the_admin_role_cant_be_changed(sammy: SammyDriver):
    assert sammy.admin_role_was_protected()


@scenario("role-management.feature", "The admin role can't be deleted")
def test_the_admin_role_cant_be_deleted():
    pass


@when(parsers.parse('I delete the role "{role}"'))
def i_delete_the_role(sammy: SammyDriver, role: str):
    sammy.delete_role(role)


@then(parsers.parse('the role "{role}" still exists'))
def the_role_still_exists(sammy: SammyDriver, role: str):
    assert sammy.role_exists(role)


@scenario("role-management.feature", "A role that someone holds can't be deleted")
def test_a_role_that_someone_holds_cant_be_deleted():
    pass


@then("I am told the role is still in use")
def i_am_told_the_role_is_still_in_use(sammy: SammyDriver):
    assert sammy.role_was_in_use()


@scenario("role-management.feature", "A role that nobody holds can be deleted")
def test_a_role_that_nobody_holds_can_be_deleted():
    pass


@then(parsers.parse('the role "{role}" doesn\'t exist'))
def the_role_doesnt_exist(sammy: SammyDriver, role: str):
    assert not sammy.role_exists(role)


@then(parsers.parse('Sammy has recorded that "{actor}" deleted the role "{role}"'))
def sammy_has_recorded_that_someone_deleted_a_role(sammy: SammyDriver, actor: str, role: str):
    assert sammy.has_recorded("role deleted", by=actor, role=role)


@scenario("role-management.feature", "A role name can only be used once")
def test_a_role_name_can_only_be_used_once():
    pass


@then("I am told the role name is already taken")
def i_am_told_the_role_name_is_already_taken(sammy: SammyDriver):
    assert sammy.role_name_was_taken()


@then(parsers.parse('the role "{role}" still has no permissions'))
def the_role_still_has_no_permissions(sammy: SammyDriver, role: str):
    assert sammy.permissions_of(role) == set()


@pytest.mark.built_examples(
    {"permission": "fly the plane"},
)
@scenario("role-management.feature", "A role can't be given a permission that doesn't exist")
def test_a_role_cant_be_given_a_permission_that_doesnt_exist():
    pass


@then("I am told the permission doesn't exist")
def i_am_told_the_permission_doesnt_exist(sammy: SammyDriver):
    assert sammy.permission_was_unknown()


@scenario("role-management.feature", "The last user who can manage roles keeps that permission")
def test_the_last_user_who_can_manage_roles_keeps_that_permission():
    pass


@given(parsers.parse('I am logged in as "{username}", who has the "{role}" role'))
def i_am_logged_in_as_someone_with_the_role(sammy: SammyDriver, username: str, role: str):
    sammy.add_user(username, "correct-horse")
    sammy.has_been_given_role(username, role)
    sammy.log_in(username, "correct-horse")


@given(parsers.parse('"{username}" is the only active user who can manage users and roles'))
def is_the_only_user_who_can_manage(sammy: SammyDriver, username: str):
    # Confirms the stated situation before going on: nobody else exists yet.
    assert sammy.user_count() == 1
    assert sammy.can_create_users(username)
    assert sammy.can_create_roles(username)


@then(parsers.parse('"{username}" can still create roles'))
def can_still_create_roles(sammy: SammyDriver, username: str):
    assert sammy.can_create_roles(username)


@then(parsers.parse('"{username}" can no longer create roles'))
def can_no_longer_create_roles(sammy: SammyDriver, username: str):
    assert not sammy.can_create_roles(username)


@pytest.mark.built_examples(
    {
        "action": 'create the role "viewer" that can view agents',
        "unchanged": 'the role "viewer" doesn\'t exist',
    },
    {
        "action": 'let the role "helper" manage users',
        "unchanged": 'the role "helper" still has no permissions',
    },
    {
        "action": 'delete the role "helper"',
        "unchanged": 'the role "helper" still exists',
    },
)
@scenario("role-management.feature", "Only users who can manage roles can change them")
def test_only_users_who_can_manage_roles_can_change_them():
    pass


@scenario("role-management.feature", "Managing roles requires logging in")
def test_managing_roles_requires_logging_in():
    pass


@scenario("role-management.feature", "A role's permissions go only to the people who hold it")
def test_a_roles_permissions_go_only_to_the_people_who_hold_it():
    pass


@scenario("role-management.feature", "Removing a permission affects only that role and that permission")
def test_removing_a_permission_affects_only_that_role_and_that_permission():
    pass


@scenario("role-management.feature", "Deleting a role leaves every other role as it was")
def test_deleting_a_role_leaves_every_other_role_as_it_was():
    pass


@scenario("role-management.feature", "A new role allows exactly what it was created with")
def test_a_new_role_allows_exactly_what_it_was_created_with():
    pass


@then(parsers.parse('the role "{role}" allows only {permissions}'))
def the_role_allows_only(sammy: SammyDriver, role: str, permissions: str):
    assert sammy.role_allows_only(role, permissions)


@scenario("role-management.feature", "Removing a permission leaves the role's other permissions")
def test_removing_a_permission_leaves_the_roles_other_permissions():
    pass
