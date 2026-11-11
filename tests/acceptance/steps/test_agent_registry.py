import pytest
from pytest_bdd import given, parsers, scenario, then, when

from drivers.sammy import SammyDriver


@scenario("agent-registry.feature", "An agent can be added")
def test_an_agent_can_be_added():
    pass


@pytest.mark.built_examples(
    {"short name": "HOMEWORK", "name": "Meal planner", "taken": "short name"},
    {"short name": "MEALS", "name": "Homework helper", "taken": "name"},
)
@scenario("agent-registry.feature", "An agent's short name and name can only be used once")
def test_an_agents_short_name_and_name_can_only_be_used_once():
    pass


@given(
    parsers.re(
        r'an agent "(?P<short_name>[^"]*)" called "(?P<name>[^"]*)", '
        r'described as "(?P<description>[^"]*)"'
    )
)
def an_agent(sammy: SammyDriver, short_name: str, name: str, description: str):
    sammy.has_agent(short_name, name, description)


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


@then(parsers.parse("I am told the agent's {field} is already taken"))
def i_am_told_the_agents_field_is_taken(sammy: SammyDriver, field: str):
    assert sammy.agent_field_taken() == field


@then(parsers.parse('the agent "{short_name}" is still described as "{description}"'))
def the_agent_is_still_described_as(sammy: SammyDriver, short_name: str, description: str):
    agent = sammy.agent(short_name)
    assert agent is not None and agent[1] == description
