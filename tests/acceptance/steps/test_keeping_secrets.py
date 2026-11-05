from pytest_bdd import parsers, scenario, then

from drivers.sammy import SammyDriver


@scenario("keeping-secrets.feature", "My password never appears in what Sammy records")
def test_my_password_never_appears_in_what_sammy_records():
    pass


@scenario("keeping-secrets.feature", "A mistyped password never appears in what Sammy records")
def test_a_mistyped_password_never_appears_in_what_sammy_records():
    pass


@then(parsers.parse('nothing Sammy has recorded contains "{secret}"'))
def nothing_sammy_has_recorded_contains(sammy: SammyDriver, secret: str):
    assert secret not in sammy.everything_recorded()
