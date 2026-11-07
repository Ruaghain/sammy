Feature: Managing users
  Admins create users, give and remove their roles, and disable them.
  A new user starts with no roles. Every change is recorded, naming who
  made it and who it was made to.

  Scenario: Setup creates the first admin
    Given no users exist
    When I run setup with the username "test.admin" and the password "correct-horse"
    Then I can log in as "test.admin" with the password "correct-horse"
    And "test.admin" has the "admin" role
    And Sammy has recorded that setup created the admin "test.admin"

  Scenario: Setup is refused once a user exists
    Given a user "test.admin" with the password "correct-horse"
    When I run setup with the username "test.intruder" and the password "other-password"
    Then I am told setup has already been completed
    And I can't log in as "test.intruder" with the password "other-password"
    And Sammy has recorded that setup was refused

  Scenario: A new user can log in and starts with no roles
    Given I am logged in as the admin "test.admin"
    When I create the user "test.user" with the password "correct-horse"
    Then I can log in as "test.user" with the password "correct-horse"
    And "test.user" has no roles
    And Sammy has recorded that "test.admin" created "test.user"

  Scenario: An admin gives a user a role
    Given I am logged in as the admin "test.admin"
    And a user "test.user" with the password "correct-horse"
    When I give "test.user" the "admin" role
    Then "test.user" can create users
    And Sammy has recorded that "test.admin" gave "test.user" the "admin" role

  Scenario: A username can only be used once
    Given I am logged in as the admin "test.admin"
    And a user "test.user" with the password "correct-horse"
    When I create the user "test.user" with the password "other-password"
    Then I am told the username is already taken
    And I can log in as "test.user" with the password "correct-horse"

  Scenario: A user can't be given a role that doesn't exist
    Given I am logged in as the admin "test.admin"
    And a user "test.user" with the password "correct-horse"
    When I give "test.user" the "no-such-role" role
    Then I am told the role doesn't exist
    And "test.user" has no roles

  Scenario Outline: Only users who can manage users can change them
    Given I am logged in as "test.helper", who has no roles
    And a user "test.other" with the password "correct-horse"
    When I <action>
    Then I am told I don't have permission
    And <unchanged>
    And Sammy has recorded that "test.helper" was refused permission to manage users

    Examples:
      | action                                                       | unchanged                                                      |
      | create the user "test.new" with the password "correct-horse" | the user "test.new" doesn't exist                              |
      | give "test.other" the "admin" role                           | "test.other" has no roles                                      |
      | disable "test.other"                                         | I can log in as "test.other" with the password "correct-horse" |

  Scenario: Managing users requires logging in
    Given I am not logged in
    When I create the user "test.new" with the password "correct-horse"
    Then I am asked to log in
    And the user "test.new" doesn't exist

  Scenario: Removing a role applies to a user who is already logged in
    Given I am logged in as the admin "test.admin"
    And "test.user" is logged in with the "admin" role
    When I remove the "admin" role from "test.user"
    Then "test.user" can no longer create users
    And Sammy has recorded that "test.admin" removed the "admin" role from "test.user"

  Scenario: The last user who can manage users keeps the admin role
    Given I am logged in as the admin "test.admin", the only user who can manage users and roles
    When I remove the "admin" role from "test.admin"
    Then I am told at least one user must be able to manage users and roles
    And "test.admin" has the "admin" role

  Scenario: The last user who can manage users can't be disabled
    Given I am logged in as the admin "test.admin", the only user who can manage users and roles
    When I disable "test.admin"
    Then I am told at least one user must be able to manage users and roles
    And "test.admin" can still log in

  Scenario: A disabled user is refused like any other failed login
    Given a user "test.user" with the password "correct-horse"
    And "test.user" has been disabled
    When I log in as "test.user" with the password "correct-horse"
    Then I am not logged in
    And I am told my username or password is incorrect
    And Sammy has recorded that a login as "test.user" was refused

  Scenario: Disabling a user ends their session
    Given I am logged in as the admin "test.admin"
    And "test.user" is logged in
    When I disable "test.user"
    Then "test.user" is no longer logged in
    And Sammy has recorded that "test.admin" disabled "test.user"

  Scenario: A user can't be given a role they already hold
    Given I am logged in as the admin "test.admin"
    And a user "test.user" with the password "correct-horse"
    And "test.user" has been given the "admin" role
    When I give "test.user" the "admin" role
    Then I am told "test.user" already has the "admin" role
    And "test.user" has the "admin" role

  Scenario: Giving a role affects only that user
    Given I am logged in as the admin "test.admin"
    And a user "test.other" with the password "battery-staple"
    And a user "test.user" with the password "correct-horse"
    When I give "test.other" the "admin" role
    Then "test.other" has the "admin" role
    And "test.user" has no roles

  Scenario: Someone else being an admin doesn't let me manage users
    Given I am logged in as "test.helper", who has no roles
    And a user "test.later" with the "admin" role
    When I create the user "test.new" with the password "correct-horse"
    Then I am told I don't have permission
    And the user "test.new" doesn't exist

  Scenario: Removing a role affects only that user
    Given I am logged in as the admin "test.admin"
    And "test.user" is logged in with the "admin" role
    And "test.zed" is logged in with the "admin" role
    When I remove the "admin" role from "test.user"
    Then "test.user" can no longer create users
    But "test.admin" can still create users
    And "test.zed" can still create users

  Scenario: Disabling a user affects only that user
    Given I am logged in as the admin "test.admin"
    And "test.user" is logged in
    And "test.zed" is logged in
    When I disable "test.user"
    Then "test.user" is no longer logged in
    But "test.zed" is still logged in
    And "test.zed" can still log in
    And "test.admin" can still log in
    And "test.admin" can still create users

  Scenario: A disabled admin doesn't count as someone who can manage users
    Given I am logged in as the admin "test.admin"
    And "test.other" is logged in with the "admin" role
    And "test.other" has been disabled
    When I remove the "admin" role from "test.admin"
    Then I am told at least one user must be able to manage users and roles
    And "test.admin" has the "admin" role
