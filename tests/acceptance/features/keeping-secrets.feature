Feature: Keeping secrets
  Passwords and sessions are never written down where someone could
  read them: not in Sammy's database, and not in anything it logs.

  Scenario: My password never appears in what Sammy records
    Given a user "test.user" with the password "correct-horse"
    When I log in as "test.user" with the password "correct-horse"
    Then nothing Sammy has recorded contains "correct-horse"

  Scenario: A mistyped password never appears in what Sammy records
    Given a user "test.user" with the password "correct-horse"
    When I log in as "test.user" with the password "wrong-password"
    Then nothing Sammy has recorded contains "wrong-password"

  Scenario: My session never appears in what Sammy records
    Given a user "test.user" with the password "correct-horse"
    When I log in as "test.user" with the password "correct-horse"
    Then nothing Sammy has recorded contains my session
