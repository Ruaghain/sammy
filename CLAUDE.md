# Sammy

Python agent suite + from-scratch chat/web interface, calling models on the homelab Ollama VM. This file is the build-facing conventions doc for this repo specifically.

## Project layout

- `uv` workspace: one shared lockfile and `.venv` at the root.
- `agent/<name>/` - one package per agent. Create it from the repo root with
  `uv init --package agent/<name>` (this registers it as a workspace member),
  check its `requires-python` is `">=3.14"`, then `uv sync`.
- `libs/core/` - shared contracts only (`Agent` protocol, `ModelClient`
  protocol, model clients). No business logic.
- `web/` - the eventual from-scratch web UI/server.
- `tools/` - repo tooling (e.g. the feature-issue sync), unit tested under
  `tools/tests/`. Not product code, so outside the ATDD loop and mutation
  testing.
- **Monolith first.** Agents are Python packages imported directly by
  whichever process runs them (CLI now, `web/`'s backend later), not
  separately deployed services, until something concrete forces a split.

## Model configuration

- Configured through environment variables, never hardcoded:
  - `SAMMY_OLLAMA_URL` - address of the Ollama VM.
  - `SAMMY_<AGENT>_MODEL` - model per agent (e.g. `SAMMY_ORCHESTRATOR_MODEL`).
- Local by default. An agent uses a frontier model (e.g. Claude) only when
  its provider is explicitly set to it and `ANTHROPIC_API_KEY` is present.
- A local `.env` file is supported for development and is gitignored.

## Public repo: no real household data

This repo is public. Everything committed, plus issue and PR text, is
visible to anyone.
- Test data, fixtures, fakes, prompts, examples and docs use made-up values
  only: never real names of household members, calendar entries, addresses,
  device names, MAC/IP addresses, hostnames, SSIDs or network topology.
- Use reserved or obviously fictional values: `192.0.2.0/24`,
  `198.51.100.0/24` and `203.0.113.0/24` for IPv4, `2001:db8::/32` for IPv6,
  `example.com` / `*.example` for domains, and invented names.
- Secrets and real configuration live only in `.env` (gitignored) or the
  environment, never in code, tests or issue text.
- If real data is needed to reproduce a problem, anonymise it first, or ask
  before committing anything.

## Work tracking (GitHub Issues)

- Every piece of work has an issue, on the "Sammy" GitHub Project board
  (new issues and PRs are auto-added; closing/merging moves them to Done).
  - **Task** (`task` label) - non-feature work: scaffolding, tooling, infra,
    docs. Created by hand from the Task form.
  - **Feature** (`feature` label) - one `.feature` file. Created by the agent.
  - **Scenario** (`scenario` label) - one scenario or `Examples` row, a
    **sub-issue** of its Feature. Created by the agent.
- Don't start work that has no issue - create or ask for one first. The
  only exception is the spec-only PR below.

### Feature flow
1. **Spec PR (human).** On a `spec/<feature-name>` branch cut from `master`,
   the human writes `tests/acceptance/features/<name>.feature` with all its
   scenarios and merges it in a PR containing only that file. No issue
   needed. Merging is the approval of every scenario in it.
2. **Generate issues (automatic).** When the spec PR merges, the
   `Feature issues` workflow (`.github/workflows/feature-issues.yml`, running
   `tools/sync_feature_issues.py`) creates the Feature issue and one Scenario
   sub-issue per scenario / `Examples` row, with its Gherkin and
   "Approved: merged in PR #<spec PR>". It is create-only: it never edits or
   closes issues, and comments on the Feature issue when a tracked scenario
   changes or disappears. If issues are missing, re-run it
   (`gh workflow run feature-issues.yml`) rather than creating them by hand.
3. **One scenario at a time (agent).** For the next Scenario issue:
   create the branch (`gh issue develop <n> --checkout`), move the Scenario
   and its Feature to **In Progress** on the board (`gh project item-edit`),
   then run the ATDD loop below and open a PR with `Closes #<n>`, filling in
   the PR template's checklist. Stop for review; don't start the next
   scenario until asked.
4. **Finish.** When the last Scenario issue is closed, close the Feature issue.
- A scenario that needs changing, or a new one (e.g. to kill a surviving
  mutant), goes through another spec PR by the human, then a new Scenario
  sub-issue. The agent never edits `.feature` files (a PreToolUse hook in
  `.claude/settings.json` blocks it).
- When asked to review a draft spec, give suggestions in the conversation:
  wording, missing or redundant scenarios, `Examples` rows, implementation
  detail leaking into the Gherkin, whether each scenario makes sense in
  context. The human applies them.
- Task issues follow step 3 too: branch from the issue, set In Progress,
  PR with `Closes #<n>`.
- Never commit on `master`; it only changes through merged PRs. GitHub
  branch protection isn't available (private repo, free plan), so
  `.githooks/pre-commit` rejects commits on `master` locally. Each clone
  enables it once with `git config core.hooksPath .githooks`.

## Acceptance-Test-Driven Development (ATDD)

Every behavioural change goes through this loop, one scenario at a time:

1. **Write the acceptance test first**, in Given/When/Then form, in the
   language of the problem domain - no class names, no selectors, no
   endpoints, no SQL. Add it under `tests/acceptance/`.
2. **Run it and confirm it fails (red).** If it already passes, the
   scenario is wrong or redundant - don't proceed until it's genuinely red.
3. **Implement until it passes (green).** Full freedom over *how*; zero
   freedom over *what* the scenario requires.
   - **Run mutation testing on the changed lines** (see below) and propose
     scenarios for any survivors, so they're visible in the review.
4. **Review and commit as one small, reviewable step.** Then move to the
   next scenario. Don't batch multiple scenarios into one large change.

### Rules
- Never edit, delete, or weaken anything under `tests/acceptance/` to make
  a test pass. If a scenario seems wrong, stop and ask - don't "fix" the test.
- Acceptance tests are written (or explicitly approved) by a human before
  the implementation exists, not generated from the code afterwards.
- Keep implementation detail out of the test case itself - that belongs in
  the protocol driver layer below it.
- One scenario (or one `Examples` row) per change. Stop once it's green and
  wait for review before starting the next - don't batch several scenarios
  into one unreviewed diff.
- Acceptance tests never call Ollama or any real model. Model calls are
  faked by injecting a fake `ModelClient` from the driver layer, so the
  suite is fast, deterministic and runs without the Ollama VM.
- Work on a feature branch and merge to `master` through a PR.

### Acceptance test mechanics
- `tests/acceptance/features/*.feature` - Gherkin scenarios.
- `tests/acceptance/steps/test_*.py` - `pytest-bdd` step definitions. Bind
  scenarios one at a time with `@scenario("<name>.feature", "<scenario name>")`
  (paths relative to `features/`), added in that scenario's PR. Never use
  `scenarios("<name>.feature")`: it binds every scenario in the file, so
  ones not yet built would fail on `master`. Unbound scenarios are ignored.
- `tests/acceptance/drivers/` - the driver the steps talk to Sammy through,
  plus fakes such as the fake `ModelClient`. Import as `drivers.<module>`.
  The driver is the one seam: if the interface moves from CLI to web, only
  the driver changes, not the feature files.

### Unit tests
- Each agent's unit tests live in `agent/<name>/tests/`. Add them inside-out
  as the acceptance test exposes the need, not speculatively.
- Unit tests are implementation detail: they can be rewritten or deleted
  during refactoring. The "never weaken" rule applies to `tests/acceptance/`
  only.

### Running tests
- `uv run pytest` - everything.
- `uv run pytest tests/acceptance` - acceptance tests only.
- `uv run pytest agent` - agent unit tests only.
- `uv run pytest tools` - tooling tests only.

### Mutation testing (cosmic-ray)
- Config lives in `cosmic-ray.toml` at the repo root; it mutates everything
  under `agent/` (excluding `agent/*/tests/`) and runs only the acceptance
  tests as the kill check, so a survivor always points at a scenario gap.
  Session files (`*.sqlite`) are gitignored.
- After a scenario goes green, run cosmic-ray scoped to the lines changed
  relative to `master` (committed or not; once changes are committed onto
  `master` itself there is nothing to compare, hence the feature-branch rule):
  ```
  uv run cosmic-ray init cosmic-ray.toml session.sqlite --force
  uv run cr-filter-git --config cosmic-ray.toml session.sqlite
  uv run cosmic-ray exec cosmic-ray.toml session.sqlite
  uv run cr-report session.sqlite
  ```
- A surviving mutant means the acceptance scenario has a gap, not that the
  implementation needs hardening. Fix it by adding a scenario or `Examples`
  row that would catch it — don't chase the mutation score by tweaking code.
- Surviving mutants fall under the same rule as weakening a test: don't
  silently accept them to get a change merged. If a mutant seems genuinely
  not worth catching (e.g. equivalent mutant, no behavioural difference),
  say so in the PR rather than ignoring it.
- Run the same commands without the `cr-filter-git` step across the whole of
  `agent/` as a periodic gate (nightly CI / pre-release), not per-PR —
  full-suite runs are too slow for the per-commit loop above.
- Scope: cosmic-ray only covers `agent/` (Python). Add `libs` to
  `module-path` in `cosmic-ray.toml` once `libs/core/` exists (every listed
  path must exist). `web/` has no mutation coverage yet — out of scope
  until/unless a JS equivalent (Stryker) gets added.
- New scenarios or `Examples` rows to kill survivors are still acceptance
  tests, so they're proposed in the PR for a human to approve, never added
  silently. Once approved they go in via a spec PR (see Feature flow).

