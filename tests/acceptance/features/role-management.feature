Feature: Managing roles

    Scenario: A role gives its permissions to the users who hold it
      Given I am logged in as an admin
      And a user "test.user" with the password "correct-horse"
      When I create the role "user manager" that can manage users
      And I give "test.user" the "user manager" role
      Then "test.user" can create users
      But "test.user" can't create roles

    Scenario: A user's permissions come from all of their roles
      Given a role "user manager" that can manage users
      And a role "role manager" that can manage roles
      And a user "test.user" with the roles "user manager" and "role manager"
      Then "test.user" can create users
      And "test.user" can create roles

    Scenario: A user with no roles can log in but can't manage anything
      Given a user "test.user" with the password "correct-horse" and no roles
      When I log in as "test.user" with the password "correct-horse"
      Then I am logged in as "test.user"
      But I can't create users
      And I can't create roles

    Scenario: Adding a permission to a role applies to users who are already logged in
      Given I am logged in as an admin
      And a role "helper" with no permissions
      And "test.user" is logged in with the "helper" role
      When I let the role "helper" manage users
      Then "test.user" can now create users

    Scenario: Removing a permission from a role applies to users who are already logged in
      Given I am logged in as an admin
      And a role "user manager" that can manage users
      And "test.user" is logged in with the "user manager" role
      When I stop the role "user manager" from managing users
      Then "test.user" can no longer create users

    Scenario: The admin role can't be changed
      Given I am logged in as an admin
      When I stop the role "admin" from managing users
      Then I am told the admin role can't be changed
      And I can still create users

    Scenario: The admin role can't be deleted
      Given I am logged in as an admin
      When I delete the role "admin"
      Then I am told the admin role can't be changed
      And the role "admin" still exists

    Scenario: A role that someone holds can't be deleted
      Given I am logged in as an admin
      And a role "user manager" that can manage users
      And a user "test.user" with the roles "user manager"
      When I delete the role "user manager"
      Then I am told the role is still in use
      And "test.user" can still create users

    Scenario: A role that nobody holds can be deleted
      Given I am logged in as an admin
      And a role "user manager" that can manage users
      When I delete the role "user manager"
      Then the role "user manager" doesn't exist

    Scenario: A role name can only be used once
      Given I am logged in as an admin
      And a role "helper" with no permissions
      When I create the role "helper" that can manage users
      Then I am told the role name is already taken
      And the role "helper" still has no permissions

    Scenario Outline: A role can't be given a permission that doesn't exist
      Given I am logged in as an admin
      When I create the role "helper" that can <permission>
    Given I am logged in as an admin
    When I create the role "helper" that can <permission>
    Then I am told the permission doesn't exist
    And the role "helper" doesn't exist

    Examples:
      | permission                      |
      | fly the plane                   |
      | use the agent "no-such-agent"   |

  Scenario: The last user who can manage roles keeps that permission
    Given "test.manager" is the only active user who can manage users and roles
    And that comes from their "people manager" role
    And I am logged in as "test.manager"
    When I stop the role "people manager" from managing roles
    Then I am told at least one user must be able to manage users and roles
    And I can still create roles

  Scenario Outline: Only users who can manage roles can change them
    Given I am logged in as a user with no roles
    And a role "helper" with no permissions
    When I <action>
    Then I am told I don't have permission
    And <unchanged>

    Examples:
      | action                                      | unchanged                              |
      | create the role "viewer" that can view agents | the role "viewer" doesn't exist      |
      | let the role "helper" manage users          | the role "helper" still has no permissions |
      | delete the role "helper"                    | the role "helper" still exists         |

  Scenario: Managing roles requires logging in
    Given I am not logged in
    When I create the role "viewer" that can view agents
    Then I am asked to log in
    And the user "test.new" doesn't exist
