from sync_feature_issues import Issue, parse_feature, plan, scenario_body

PATH = "tests/acceptance/features/routing.feature"

FEATURE = """\
Feature: Routing

  Background:
    Given Sammy is running

  Scenario: Routes a review request
    When I ask for a code review
    Then the code reviewer handles it

  @slow
  Scenario Outline: Routes by keyword <word>
    When I say <word>
    Then <agent> handles it

    Examples:
      | word   | agent    |
      | review | reviewer |
      | ping   | network  |

  Rule: Unknown requests
    Scenario: Nothing matches
      When I say gibberish
      Then I am asked to rephrase
"""


def issues_for(feature, keys=None, sha_of=None, feature_number=1):
    issues = [Issue(feature_number, 100, f"<!-- sammy-feature: {feature.path} -->")]
    for n, s in enumerate(feature.scenarios, start=2):
        if keys is None or s.key in keys:
            body = scenario_body(feature, s, "Approved.")
            if sha_of and s.key in sha_of:
                body = body.replace(s.sha, sha_of[s.key])
            issues.append(Issue(n, 100 + n, body))
    return issues


def test_each_scenario_and_examples_row_becomes_its_own_scenario():
    feature = parse_feature(PATH, FEATURE)

    assert feature.name == "Routing"
    assert [s.key for s in feature.scenarios] == [
        "Routes a review request",
        "Routes by keyword <word> (word=review, agent=reviewer)",
        "Routes by keyword <word> (word=ping, agent=network)",
        "Nothing matches",
    ]


def test_scenario_gherkin_is_its_own_block_without_trailing_tags():
    first, row, _, in_rule = parse_feature(PATH, FEATURE).scenarios

    assert first.gherkin == (
        "  Scenario: Routes a review request\n"
        "    When I ask for a code review\n"
        "    Then the code reviewer handles it"
    )
    assert row.gherkin == (
        "  Scenario Outline: Routes by keyword <word>\n"
        "    When I say <word>\n"
        "    Then <agent> handles it\n"
        "\n"
        "    Examples:\n"
        "      | word   | agent    |\n"
        "      | review | reviewer |"
    )
    assert "@slow" not in first.gherkin
    assert in_rule.gherkin.strip().startswith("Scenario: Nothing matches")


def test_adding_an_examples_row_does_not_change_the_existing_rows():
    before = parse_feature(PATH, FEATURE)
    after = parse_feature(PATH, FEATURE.replace(
        "      | ping   | network  |\n",
        "      | ping   | network  |\n      | remind | calendar |\n",
    ))

    result = plan(after, issues_for(before), changed=True)

    assert [s.key for s in result.new_scenarios] == [
        "Routes by keyword <word> (word=remind, agent=calendar)"
    ]
    assert result.notices == []


def test_untracked_feature_creates_feature_and_every_scenario():
    feature = parse_feature(PATH, FEATURE)

    result = plan(feature, [], changed=True)

    assert result.feature_number is None
    assert result.new_scenarios == feature.scenarios
    assert result.notices == []


def test_only_missing_scenarios_are_created():
    feature = parse_feature(PATH, FEATURE)
    issues = issues_for(feature, keys={"Routes a review request", "Nothing matches"})

    result = plan(feature, issues, changed=True)

    assert result.feature_number == 1
    assert [s.key for s in result.new_scenarios] == [
        "Routes by keyword <word> (word=review, agent=reviewer)",
        "Routes by keyword <word> (word=ping, agent=network)",
    ]


def test_issues_for_other_feature_files_are_ignored():
    feature = parse_feature(PATH, FEATURE)
    other = parse_feature("tests/acceptance/features/other.feature", FEATURE)

    result = plan(feature, issues_for(other), changed=True)

    assert result.feature_number is None
    assert len(result.new_scenarios) == 4


def test_changed_and_removed_scenarios_are_reported_not_touched():
    feature = parse_feature(PATH, FEATURE)
    issues = issues_for(feature, sha_of={"Nothing matches": "000000000000"})
    issues.append(Issue(9, 109, f"<!-- sammy-scenario: {PATH} :: Old scenario -->"))

    result = plan(feature, issues, changed=True)

    assert result.new_scenarios == []
    assert result.notices == [
        "`Nothing matches` (#5) has changed since its issue was created.",
        "`Old scenario` (#9) is no longer in the file.",
    ]


def test_no_notices_for_files_not_changed_in_this_push():
    feature = parse_feature(PATH, FEATURE)
    issues = issues_for(feature, sha_of={"Nothing matches": "000000000000"})

    assert plan(feature, issues, changed=False).notices == []
