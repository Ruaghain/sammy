Closes #

<!--
Keep the checklist that matches this PR and delete the other.
Spec-only PR (a new or changed .feature file and nothing else)?
Delete the "Closes" line and everything below; merging this PR approves its scenarios.
-->

## Checklist (Scenario PR)
- [ ] Linked to its Scenario issue above
- [ ] Only this scenario was bound (`@scenario(...)`, not `scenarios(...)`)
- [ ] Scenario was confirmed red before implementation
- [ ] Scenario is green (`uv run pytest`)
- [ ] Nothing under `tests/acceptance/` was edited, deleted or weakened to get to green
- [ ] cosmic-ray run on the changed lines
- [ ] Surviving mutants: none / listed below with new scenarios proposed (or why they're not worth catching)

## Checklist (Task PR)
- [ ] Linked to its Task issue above
- [ ] No behaviour change, or the change is covered by a merged spec
- [ ] All tests still green (`uv run pytest`)
- [ ] Nothing under `tests/acceptance/` was edited, deleted or weakened
- [ ] cosmic-ray run on the changed lines under `agent/` (n/a if none)
- [ ] Surviving mutants: none / listed below with new scenarios proposed (or why they're not worth catching)

## Surviving mutants
<!-- cr-report output, or "none" -->
