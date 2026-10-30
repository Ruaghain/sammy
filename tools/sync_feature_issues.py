"""Create Feature and Scenario issues from the .feature files on master.

Create-only: missing issues are added, existing ones are never edited or
closed. When a tracked scenario changes or disappears from a file changed in
this push, the Feature issue gets a comment so a human decides what to do.
Issues are matched to the file through hidden markers in their bodies.
"""

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

FEATURES_DIR = Path("tests/acceptance/features")
FEATURE_MARKER = re.compile(r"<!-- sammy-feature: (.+?) -->")
SCENARIO_MARKER = re.compile(r"<!-- sammy-scenario: (.+?) :: (.+?) -->")
GHERKIN_MARKER = re.compile(r"<!-- sammy-gherkin: (\w+) -->")


@dataclass(frozen=True)
class Scenario:
    key: str  # scenario name, plus the row values for an Examples row
    gherkin: str

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.gherkin.encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Feature:
    path: str
    name: str
    scenarios: list[Scenario]


@dataclass(frozen=True)
class Issue:
    number: int
    id: int
    body: str


@dataclass
class Plan:
    feature_number: int | None  # None: the Feature issue must be created
    new_scenarios: list[Scenario] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


def parse_feature(path: str, text: str) -> Feature:
    feature = Parser().parse(TokenScanner(text))["feature"]
    lines = text.splitlines()

    nodes = []  # (kind, node) for every top-level and Rule child, in file order
    for child in feature["children"]:
        if "rule" in child:
            nodes.append(("rule", child["rule"]))
            nodes.extend(next(iter(c.items())) for c in child["rule"]["children"])
        else:
            nodes.append(next(iter(child.items())))
    starts = [node["location"]["line"] for _, node in nodes]

    scenarios = []
    for i, (kind, node) in enumerate(nodes):
        if kind != "scenario":
            continue
        end = starts[i + 1] - 1 if i + 1 < len(starts) else len(lines)
        block = lines[node["location"]["line"] - 1 : end]
        while block and (not block[-1].strip() or block[-1].strip().startswith("@")):
            block.pop()
        if not node["examples"]:
            scenarios.append(Scenario(node["name"], "\n".join(block)))
            continue

        # One Scenario per Examples row, holding only the outline's steps and
        # that row, so adding or changing another row doesn't touch it.
        steps = lines[node["location"]["line"] - 1 : node["examples"][0]["location"]["line"] - 1]
        while steps and not steps[-1].strip():
            steps.pop()
        for ex in node["examples"]:
            header = ex["tableHeader"]
            for row in ex["tableBody"]:
                values = ", ".join(
                    f"{h['value']}={c['value']}" for h, c in zip(header["cells"], row["cells"])
                )
                gherkin = "\n".join(
                    steps
                    + [""]
                    + [lines[ex["location"]["line"] - 1]]
                    + [lines[header["location"]["line"] - 1], lines[row["location"]["line"] - 1]]
                )
                scenarios.append(Scenario(f"{node['name']} ({values})", gherkin))
    return Feature(path, feature["name"], scenarios)


def plan(feature: Feature, issues: list[Issue], changed: bool) -> Plan:
    feature_number = next(
        (i.number for i in issues if (m := FEATURE_MARKER.search(i.body)) and m[1] == feature.path),
        None,
    )
    tracked = {}  # scenario key -> (issue number, gherkin sha when created)
    for issue in issues:
        m = SCENARIO_MARKER.search(issue.body)
        if m and m[1] == feature.path:
            sha = GHERKIN_MARKER.search(issue.body)
            tracked[m[2]] = (issue.number, sha[1] if sha else None)

    result = Plan(feature_number, [s for s in feature.scenarios if s.key not in tracked])
    if changed:
        current = {s.key: s for s in feature.scenarios}
        for key, (number, sha) in tracked.items():
            if key not in current:
                result.notices.append(f"`{key}` (#{number}) is no longer in the file.")
            elif current[key].sha != sha:
                result.notices.append(f"`{key}` (#{number}) has changed since its issue was created.")
    return result


def feature_body(feature: Feature) -> str:
    return (
        f"Feature file: `{feature.path}`\n\n"
        "Scenarios are tracked as sub-issues, one branch and PR each.\n\n"
        f"<!-- sammy-feature: {feature.path} -->"
    )


def scenario_body(feature: Feature, scenario: Scenario, approval: str) -> str:
    return (
        f"From `{feature.path}`.\n\n"
        f"```gherkin\n{scenario.gherkin}\n```\n\n"
        f"{approval}\n\n"
        f"<!-- sammy-scenario: {feature.path} :: {scenario.key} -->\n"
        f"<!-- sammy-gherkin: {scenario.sha} -->"
    )


class GitHub:
    def __init__(self, repo: str, dry_run: bool):
        self.repo = repo
        self.dry_run = dry_run

    def _api(self, *args: str) -> str:
        return subprocess.run(
            ["gh", "api", *args], check=True, capture_output=True, text=True
        ).stdout

    def issues(self, label: str) -> list[Issue]:
        out = self._api(
            "--paginate",
            f"repos/{self.repo}/issues?labels={label}&state=all&per_page=100",
            "--jq", ".[] | {number, id, body}",
        )
        return [Issue(d["number"], d["id"], d["body"] or "") for d in map(json.loads, out.splitlines())]

    def spec_pr(self, sha: str) -> int | None:
        out = self._api(f"repos/{self.repo}/commits/{sha}/pulls", "--jq", ".[0].number // empty")
        return int(out) if out.strip() else None

    def create_issue(self, title: str, body: str, label: str) -> Issue:
        if self.dry_run:
            print(f"[dry-run] create {label} issue: {title}")
            return Issue(0, 0, body)
        d = json.loads(self._api(
            f"repos/{self.repo}/issues", "-f", f"title={title}", "-f", f"body={body}",
            "-f", f"labels[]={label}",
        ))
        print(f"created #{d['number']}: {title}")
        return Issue(d["number"], d["id"], body)

    def add_sub_issue(self, parent: int, child: Issue) -> None:
        if self.dry_run:
            return
        self._api(f"repos/{self.repo}/issues/{parent}/sub_issues", "-F", f"sub_issue_id={child.id}")

    def comment(self, number: int, body: str) -> None:
        if self.dry_run:
            print(f"[dry-run] comment on #{number}:\n{body}")
            return
        self._api(f"repos/{self.repo}/issues/{number}/comments", "-f", f"body={body}")


def sync(github: GitHub, sha: str, changed: set[str]) -> None:
    issues = github.issues("feature") + github.issues("scenario")
    pr = github.spec_pr(sha)
    approval = f"Approved: merged in PR #{pr}." if pr else f"Approved: on `master` at {sha}."

    for path in sorted(FEATURES_DIR.rglob("*.feature")):
        feature = parse_feature(path.as_posix(), path.read_text())
        todo = plan(feature, issues, changed=path.as_posix() in changed)

        parent = todo.feature_number
        if parent is None:
            parent = github.create_issue(
                f"[Feature]: {feature.name}", feature_body(feature), "feature"
            ).number
        for scenario in todo.new_scenarios:
            child = github.create_issue(
                f"[Scenario]: {scenario.key}", scenario_body(feature, scenario, approval), "scenario"
            )
            github.add_sub_issue(parent, child)
        if todo.notices:
            github.comment(parent, "\n".join(
                [f"`{feature.path}` changed on `master` ({sha}). Existing scenario issues were left as they are:", ""]
                + [f"- {n}" for n in todo.notices]
            ))


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--repo", required=True, help="owner/name")
    args.add_argument("--sha", required=True, help="commit on master being synced")
    args.add_argument("--changed", nargs="*", default=[], help="feature files changed in this push")
    args.add_argument("--dry-run", action="store_true")
    a = args.parse_args()
    sync(GitHub(a.repo, a.dry_run), a.sha, set(a.changed))


if __name__ == "__main__":
    main()
