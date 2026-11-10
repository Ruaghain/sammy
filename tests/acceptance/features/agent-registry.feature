Feature: The agent registry
  Each agent has a short name, a name and a description. The short name
  (capital letters, digits and underscores, e.g. "WEATHER_AGENT") identifies
  the agent everywhere else, such as in the permission to use it ("use agent
  WEATHER_AGENT"), so it never changes; the name and description can. Names
  are unique. The orchestrator gives its model the descriptions to choose an
  agent, so every agent needs one. Adding an agent, renaming it, changing its
  description and removing it are recorded, naming who did it.

  Scenario: An agent can be added
    Given I am logged in as the admin "test.admin"
    When I add the agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    Then the agent "HOMEWORK" is called "Homework helper" and described as "Helps with school homework"
    And Sammy has recorded that "test.admin" added the agent "HOMEWORK"

  Scenario Outline: An agent's short name and name can only be used once
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    When I add the agent "<short name>" called "<name>", described as "Plans the week's meals"
    Then I am told the agent's <taken> is already taken
    And the agent "HOMEWORK" is still described as "Helps with school homework"

    Examples:
      | short name | name            | taken      |
      | HOMEWORK   | Meal planner    | short name |
      | MEALS      | Homework helper | name       |

  Scenario Outline: A short name is capital letters, digits and underscores
    Given I am logged in as the admin "test.admin"
    When I add the agent "<short name>" called "Weather", described as "Gives the forecast"
    Then I am told the short name isn't valid
    And there are no agents

    Examples:
      | short name    |
      | weather_agent |
      | WEATHER AGENT |
      | WEATHER-AGENT |
      | 1WEATHER      |
      |               |

  Scenario Outline: Every agent needs a name and a description
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    When I <action>
    Then I am told the agent's <missing> can't be blank
    And <unchanged>

    Examples:
      | action                                                                     | missing     | unchanged|
      | add the agent "MEALS" called "", described as "Plans the week's meals"     | name        | the agent "MEALS" doesn't exist|
      | add the agent "MEALS" called "   ", described as "Plans the week's meals"  | name        | the agent "MEALS" doesn't exist|
      | add the agent "MEALS" called "Meal planner", described as ""               | description | the agent "MEALS" doesn't exist|
      | add the agent "MEALS" called "Meal planner", described as "   "            | description | the agent "MEALS" doesn't exist|
      | rename the agent "HOMEWORK" to ""                                          | name        | the agent "HOMEWORK" is called "Homework helper" and described as "Helps with school homework" |
      | describe the agent "HOMEWORK" as ""                                        | description | the agent "HOMEWORK" is called "Homework helper" and described as "Helps with school homework" |

  Scenario: An agent's description can be changed
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    When I describe the agent "HOMEWORK" as "Helps with homework and revision"
    Then the agent "HOMEWORK" is described as "Helps with homework and revision"
    And Sammy has recorded that "test.admin" changed the description of the agent "HOMEWORK"

  Scenario: An agent can be renamed, keeping its short name
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    And a role "student" that can use the agent "HOMEWORK"
    When I rename the agent "HOMEWORK" to "Study buddy"
    Then the agent "HOMEWORK" is called "Study buddy" and described as "Helps with school homework"
    And the role "student" allows only using the agent "HOMEWORK"
    And Sammy has recorded that "test.admin" renamed the agent "HOMEWORK"

  Scenario: An agent can't be renamed to a name another agent has
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    And an agent "MEALS" called "Meal planner", described as "Plans the week's meals"
    When I rename the agent "MEALS" to "Homework helper"
    Then I am told the agent's name is already taken
    And the agent "MEALS" is called "Meal planner" and described as "Plans the week's meals"

  Scenario: A role can be allowed to use an agent that exists
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    When I create the role "student" that can use the agent "HOMEWORK"
    Then the role "student" allows only using the agent "HOMEWORK"

  Scenario: A role can't be allowed to use an agent that doesn't exist
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    When I create the role "student" that can use the agent "NO_SUCH_AGENT"
    Then I am told the permission doesn't exist
    And the role "student" doesn't exist

  Scenario: An agent can be removed
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    And an agent "MEALS" called "Meal planner", described as "Plans the week's meals"
    And a role "cook" that can use the agent "MEALS"
    When I remove the agent "HOMEWORK"
    Then the agent "HOMEWORK" doesn't exist
    And the agent "MEALS" is still described as "Plans the week's meals"
    And Sammy has recorded that "test.admin" removed the agent "HOMEWORK"

  Scenario: An agent that a role allows can't be removed
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    And a role "student" that can use the agent "HOMEWORK"
    When I remove the agent "HOMEWORK"
    Then I am told the agent is still in use
    And the agent "HOMEWORK" is still described as "Helps with school homework"

  Scenario: An agent can be removed once no role allows it
    Given I am logged in as the admin "test.admin"
    And an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    And a role "student" that can use the agent "HOMEWORK"
    When I stop the role "student" from using the agent "HOMEWORK"
    And I remove the agent "HOMEWORK"
    Then the agent "HOMEWORK" doesn't exist

  Scenario Outline: Users who can view or manage agents see all of them
    Given an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    And an agent "MEALS" called "Meal planner", described as "Plans the week's meals"
    And a role "<role>" that can <permission>
    And I am logged in as "test.user", who has the "<role>" role
    When I list the agents
    Then I see the agents "HOMEWORK" and "MEALS"

    Examples:
      | role         | permission    |
      | agent viewer | view agents   |
      | agent keeper | manage agents |

  Scenario: Only users who can view agents can list them
    Given I am logged in as "test.helper", who has no roles
    When I list the agents
    Then I am told I don't have permission
    And Sammy has recorded that "test.helper" was refused permission to view agents

  Scenario Outline: Only users who can manage agents can change them
    Given an agent "HOMEWORK" called "Homework helper", described as "Helps with school homework"
    And a role "agent viewer" that can view agents
    And I am logged in as "test.viewer", who has the "agent viewer" role
    When I <action>
    Then I am told I don't have permission
    And <unchanged>
    And Sammy has recorded that "test.viewer" was refused permission to manage agents

    Examples:
      | action                                                                              | unchanged                      |
      | add the agent "MEALS" called "Meal planner", described as "Plans the week's meals"  | the agent "MEALS" doesn't exist |
      | rename the agent "HOMEWORK" to "Study buddy"                                        | the agent "HOMEWORK" is called "Homework helper" and described as "Helps with school homework" |
      | describe the agent "HOMEWORK" as "Plans the week's meals"                           | the agent "HOMEWORK" is called "Homework helper" and described as "Helps with school homework" |
      | remove the agent "HOMEWORK"                                                         | the agent "HOMEWORK" is called "Homework helper" and described as "Helps with school homework" |

  Scenario: Managing agents requires logging in
    Given I am not logged in
    When I add the agent "MEALS" called "Meal planner", described as "Plans the week's meals"
    Then I am asked to log in
    And the agent "MEALS" doesn't exist
