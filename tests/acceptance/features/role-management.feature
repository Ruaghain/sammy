Feature: Managing roles
  A role is a named set of permissions. Users can hold any number of
  roles and can do whatever any of them allows. The built-in "admin" role
  has every permission and can't be changed. Every change to a role is
  recorded, naming who made it.

  Scenario: A role gives its permissions to the users who hold it
    Given I am logged in as the admin "test.admin"
    And a user "test.other" with the password "battery-staple"
    And a user "test.user" with the password "correct-horse"
    When I create the role "user manager" that can manage users
    And I give "test.user" the "user manager" role
    Then "test.user" can create users
    But "test.user" can't create roles
    And "test.other" has no roles
    And Sammy has recorded that "test.admin" created the role "user manager"

  Scenario: A user's permissions come from all of their roles
    Given I am logged in as the admin "test.admin"
    And a role "user manager" that can manage users
    And a role "role manager" that can manage roles
    And "test.user" is logged in with the "user manager" role
    And "test.user" has been given the "role manager" role
    Then "test.user" can create users
    And "test.user" can create roles

  Scenario: A user with no roles can log in but can't manage anything
    Given a user "test.user" with the password "correct-horse"
    When I log in as "test.user" with the password "correct-horse"
    Then I am logged in as "test.user"
    But "test.user" can't create users
    And "test.user" can't create roles

  Scenario: Adding a permission to a role applies to users who are already logged in
    Given I am logged in as the admin "test.admin"
    And a role "helper" with no permissions
    And "test.user" is logged in with the "helper" role
    When I let the role "helper" manage users
    Then "test.user" can create users
    And Sammy has recorded that "test.admin" let the role "helper" manage users

  Scenario: Removing a permission from a role applies to users who are already logged in
    Given I am logged in as the admin "test.admin"
    And a role "user manager" that can manage users
    And "test.user" is logged in with the "user manager" role
    When I stop the role "user manager" from managing users
    Then "test.user" can no longer create users
    And Sammy has recorded that "test.admin" stopped the role "user manager" from managing users

  Scenario: The admin role can't be changed
    Given I am logged in as the admin "test.admin"
    When I stop the role "admin" from managing users
    Then I am told the admin role can't be changed
    And "test.admin" can still create users

  Scenario: The admin role can't be deleted
    Given I am logged in as the admin "test.admin"
    When I delete the role "admin"
    Then I am told the admin role can't be changed
    And the role "admin" still exists

  Scenario: A role that someone holds can't be deleted
    Given I am logged in as the admin "test.admin"
    And a role "user manager" that can manage users
    And a user "test.user" with the "user manager" role
    When I delete the role "user manager"
    Then I am told the role is still in use
    And "test.user" can still create users

  Scenario: A role that nobody holds can be deleted
    Given I am logged in as the admin "test.admin"
    And a role "user manager" that can manage users
    When I delete the role "user manager"
    Then the role "user manager" doesn't exist
    And Sammy has recorded that "test.admin" deleted the role "user manager"

  Scenario: A role name can only be used once
    Given I am logged in as the admin "test.admin"
    And a role "helper" with no permissions
    When I create the role "helper" that can manage users
    Then I am told the role name is already taken
    And the role "helper" still has no permissions

  Scenario Outline: A role can't be given a permission that doesn't exist
    Given I am logged in as the admin "test.admin"
    When I create the role "helper" that can <permission>
    Then I am told the permission doesn't exist
    And the role "helper" doesn't exist

    Examples:
      | permission                    |
      | fly the plane                 |
      | use the agent "no-such-agent" |

  Scenario: The last user who can manage roles keeps that permission
    Given a role "people manager" that can manage users and roles
    And I am logged in as "test.manager", who has the "people manager" role
    And "test.manager" is the only active user who can manage users and roles
    When I stop the role "people manager" from managing roles
    Then I am told at least one user must be able to manage users and roles
    And "test.manager" can still create roles

  Scenario Outline: Only users who can manage roles can change them
    Given I am logged in as "test.helper", who has no roles
    And a role "helper" with no permissions
    When I <action>
    Then I am told I don't have permission
    And <unchanged>
    And Sammy has recorded that "test.helper" was refused permission to manage roles

    Examples:
      | action                                        | unchanged                                  |
      | create the role "viewer" that can view agents | the role "viewer" doesn't exist            |
      | let the role "helper" manage users            | the role "helper" still has no permissions |
      | delete the role "helper"                      | the role "helper" still exists             |

  Scenario: Managing roles requires logging in
    Given I am not logged in
    When I create the role "viewer" that can view agents
    Then I am asked to log in
    And the role "viewer" doesn't exist
