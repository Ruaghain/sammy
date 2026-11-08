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


@given(parsers.parse('a role "{role}" that can {permissions}'))
def a_role_that_can(sammy: SammyDriver, role: str, permissions: str):
    sammy.has_role(role, permissions)


@then(parsers.parse('"{username}" can create roles'))
def can_create_roles(sammy: SammyDriver, username: str):
    assert sammy.can_create_roles(username)


@scenario("role-management.feature", "A user with no roles can log in but can't manage anything")
def test_a_user_with_no_roles_can_log_in_but_cant_manage_anything():
    pass


@then(parsers.parse('"{username}" can\'t create users'))
def cant_create_users(sammy: SammyDriver, username: str):
    assert not sammy.can_create_users(username)
