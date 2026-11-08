from pytest_bdd import parsers, scenario, then, when

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
