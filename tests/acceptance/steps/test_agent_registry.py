from pytest_bdd import parsers, scenario, then, when

from drivers.sammy import SammyDriver


@scenario("agent-registry.feature", "An agent can be added")
def test_an_agent_can_be_added():
    pass


@when(
    parsers.re(
        r'I add the agent "(?P<short_name>[^"]*)" called "(?P<name>[^"]*)", '
        r'described as "(?P<description>[^"]*)"'
    )
)
def i_add_the_agent(sammy: SammyDriver, short_name: str, name: str, description: str):
    sammy.add_agent(short_name, name, description)


@then(parsers.parse('the agent "{short_name}" is called "{name}" and described as "{description}"'))
def the_agent_is_called_and_described_as(
    sammy: SammyDriver, short_name: str, name: str, description: str
):
    assert sammy.agent(short_name) == (name, description)


@then(parsers.parse('Sammy has recorded that "{actor}" added the agent "{short_name}"'))
def sammy_has_recorded_that_the_agent_was_added(sammy: SammyDriver, actor: str, short_name: str):
    assert sammy.has_recorded("agent added", by=actor, agent=short_name)
