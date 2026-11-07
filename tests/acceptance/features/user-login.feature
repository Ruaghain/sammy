Feature: User login
  People log in before they can talk to Sammy, and log out when
  they're done. A failed login shows the same message whether the
  username or the password was wrong.

  Scenario: Logging in with valid details
    Given a user "test.user" with the password "correct-horse"
    When I log in as "test.user" with the password "correct-horse"
    Then I am logged in as "test.user"

  Scenario Outline: Login is refused without revealing which detail was wrong
    Given a user "test.user" with the password "correct-horse"
    And a user "test.other" with the password "battery-staple"
    When I log in as "<username>" with the password "<password>"
    Then I am not logged in
    And I am told my username or password is incorrect

    Examples:
      | username     | password       |
      | test.user    | wrong-password |
      | unknown.user | correct-horse  |
      | test.user    | Correct-Horse  |
      | test.user    |                |
      | test.user    | battery-staple |

  Scenario: Talking to Sammy requires logging in
    Given I am not logged in
    When I send Sammy a message
    Then I am asked to log in

  Scenario: Logging out
    Given I am logged in as "test.user"
    When I log out
    Then I am not logged in
    And I am asked to log in when I send Sammy a message

  Scenario: Each user logs in as themselves
    Given a user "test.user" with the password "correct-horse"
    And a user "test.other" with the password "battery-staple"
    When I log in as "test.other" with the password "battery-staple"
    Then I am logged in as "test.other"

  Scenario: Logging out leaves everyone else logged in
    Given "test.user" and "test.other" are both logged in
    When "test.user" logs out
    Then "test.other" is still logged in

Scenario: A successful login is recorded
  Given a user "test.user" with the password "correct-horse"
  When I log in as "test.user" with the password "correct-horse"
  Then Sammy has recorded that "test.user" logged in

Scenario: A refused login is recorded
  Given a user "test.user" with the password "correct-horse"
  When I log in as "test.user" with the password "wrong-password"
  Then Sammy has recorded that a login as "test.user" was refused

Scenario: Logging out is recorded
  Given I am logged in as "test.user"
  When I log out
  Then Sammy has recorded that "test.user" logged out
