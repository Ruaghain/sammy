# Sammy

Python agent suite + from-scratch chat/web interface, calling models on the homelab Ollama VM. This file is the build-facing conventions doc for this repo specifically.

## Project layout

- `uv` workspace: one shared lockfile and `.venv` at the root.
- `agent/<name>/` - one package per agent. Create it from the repo root with
  `uv init --package agent/<name>` (this registers it as a workspace member),
  check its `requires-python` is `">=3.14"`, then `uv sync`.
- `libs/core/` - shared contracts only (`Agent` protocol, `ModelClient`
  protocol, model clients). No business logic.
- `libs/accounts/` - users and login. Not an agent, and it holds business
  logic, so it doesn't belong in `libs/core/`. Product code: it follows the
  ATDD loop and is mutation tested. Create it with
  `uv init --package libs/accounts`, then add `libs` to `testpaths` in
  `pyproject.toml` and to `module-path` in `cosmic-ray.toml`.
- `web/` - the eventual from-scratch web UI/server.
- `tools/` - repo tooling (e.g. the feature-issue sync), unit tested under
  `tools/tests/`. Not product code, so outside the ATDD loop and mutation
  testing.
- **Monolith first.** Agents are Python packages imported directly by
  whichever process runs them (CLI now, `web/`'s backend later), not
  separately deployed services, until something concrete forces a split.

## Code structure

`libs/accounts` is the model; new packages follow the same shape.
- `__init__.py` only re-exports the public API. No implementation lives in it.
- One module per concern: `users.py` (`UserService`), `roles.py`
  (`RoleService`), `sessions.py` (`SessionService`), plus small supporting
  modules (`errors.py`, `passwords.py`, `audit.py`, `schema.py`,
  `tables.py`).
- The lower services own the SQL for their own tables. They take an open
  database connection and never open a transaction, so work that spans them
  succeeds or fails together. There is no separate DAO/repository layer.
- One top-level service per package (`AccountService` in `service.py`) is the
  only public entry point. It opens transactions, works out who is acting and
  whether they're allowed, enforces rules that span services (e.g. someone
  can always manage users and roles) and logs events. It contains no SQL.
- Sammy has one database. Whatever starts Sammy (CLI, web backend, the
  acceptance driver) creates the one SQLAlchemy engine and passes it to each
  package's top-level service; packages never connect by themselves.
- Each package migrates only its own tables, with its own `migrate(engine)`
  (e.g. `accounts.migrate`), run explicitly at startup before any of its
  services are created. Creating a service never changes the schema.
- Each package keeps its own exceptions in `errors.py`, under one common base
  (e.g. `AccountsError`) so callers can handle them all at once.
- A helper shared by more than one package (e.g. `audit`) moves to
  `libs/core` once a second package needs it, not before.
- Unit test files are named after the module they cover (`test_users.py`,
  `test_passwords.py`, ...) and exist only for what acceptance scenarios can't
  see: storage formats, timing, migrations. There's no unit test file per
  module by default.

## Model configuration

- Configured through environment variables, never hardcoded:
  - `SAMMY_OLLAMA_URL` - address of the Ollama VM.
  - `SAMMY_<AGENT>_MODEL` - model per agent (e.g. `SAMMY_ORCHESTRATOR_MODEL`).
- Local by default. An agent uses a frontier model (e.g. Claude) only when
  its provider is explicitly set to it and `ANTHROPIC_API_KEY` is present.
- A local `.env` file is supported for development and is gitignored.

## Logging

- Library and agent code only calls `logging.getLogger(__name__)`. Handlers
  are set up once, by whichever entry point starts Sammy (CLI now, `web/`'s
  backend later), never by library code, so tests never write log files.
- Logs go to one file, `sammy.log`, in the folder set by `SAMMY_LOG_DIR`
  (default `./logs`, gitignored). It rotates at midnight UTC into
  `sammy.log.<date>`, and files older than `SAMMY_LOG_RETENTION_DAYS`
  (default 30) are deleted. `SAMMY_LOG_LEVEL` sets the level (default
  `INFO`). Lines are plain text with UTC timestamps.
- Only one process writes the file at a time. If two ever run at once (e.g.
  the CLI and the web server), they need separate files first.
- Logs identify a user only by their `public_id` (see Stored data), never by
  username, and never contain passwords or session tokens. A refused login
  for an unknown username logs that no such user exists, without the
  username: people sometimes type their password into the username box.

## Stored data

- Users and the agent registry live in a database, at the location set by
  `SAMMY_DATABASE_URL`. Never commit a database file. Both SQLite and
  PostgreSQL are supported, through SQLAlchemy Core:
  - `sqlite:///path/to/sammy.sqlite`
  - `postgresql+psycopg://user:password@host/database`
- Write queries with SQLAlchemy Core so they run unchanged on both. Nothing
  may be specific to one database.
- The schema is created and changed only by Alembic migrations, which Sammy
  applies itself at startup through each package's `migrate(engine)` (see
  Code structure). `accounts` keeps its migrations in
  `libs/accounts/src/accounts/migrations/` and its tables in
  `accounts/tables.py`; a change to one needs the other, and a unit test
  fails if they drift apart. Add a migration with
  `SAMMY_DATABASE_URL=sqlite:///scratch.sqlite uv run alembic -c libs/accounts/alembic.ini revision -m "<change>"`.
- Each registered agent has a name and a description. The orchestrator gives
  its model the user's message and these descriptions and asks it to choose
  the best agent, so routing has no hand-written rules. An agent's model stays
  in the environment configuration above, not in the registry.
- Each user has three identifiers:
  - `id` - auto-incrementing integer primary key, used only inside the
    database (foreign keys, joins). It never leaves the database: it can
    change when data moves to another database, and it reveals how many
    users exist.
  - `public_id` - a UUIDv7 (`uuid.uuid7()`), created with the user and never
    changed. Anything that leaves the database refers to a user by it: logs
    now, URLs and APIs later.
  - `username` - unique, used only for logging in.
- Store only a salted hash of each password, made with a dedicated password
  hashing algorithm. Never log passwords or session tokens (see Logging).
- Access is controlled by roles. Permissions are fixed in code. A role is a
  named set of permissions stored in the database. A user can hold any number
  of roles, including none, and can do whatever any of their roles allows
  (there are no "deny" permissions). New users start with no roles, so access
  is always given on purpose.
- Permissions: `manage users` (create, disable, give and remove roles),
  `manage roles` (create, change and delete roles), `view agents`,
  `manage agents` (add agents, edit their descriptions) and
  `use agent <name>` (talk to that agent).
- The built-in `admin` role has every permission and can't be changed or
  deleted. A role that any user still holds can't be deleted.
- At least one active user must always have `manage users` and
  `manage roles`, from whichever roles. Anything that would break this
  (removing a role from someone, changing a role, disabling a user) is
  refused.
- Changes to roles and permissions apply straight away, including to users
  who are already logged in.
- The orchestrator only offers its model the agents the user is allowed to
  use, so a refusal never reveals that an agent exists.
- Refusals reveal nothing extra. Every failed login (wrong password, unknown
  user, disabled user) gets the same message and takes about as long.
- Acceptance tests use a throwaway database, set up through the driver layer
  (`tests/acceptance/drivers/database.py`): a new SQLite file per scenario,
  or a fresh PostgreSQL database per scenario when `SAMMY_TEST_DATABASE_URL`
  is set (see Running tests).

## Public repo: no real household data

This repo is public. Everything committed, plus issue and PR text, is
visible to anyone.
- Test data, fixtures, fakes, prompts, examples and docs use made-up values
  only: never real names of household members, calendar entries, addresses,
  usernames, passwords, device names, MAC/IP addresses, hostnames, SSIDs or
  network topology.
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
  context, and whether its logging is covered (below). The human applies
  them.
- Logging is specified per feature. Every feature that changes something
  (creates, changes, removes, grants, refuses) has a scenario for each event
  Sammy logs, in the form `Then Sammy has recorded that …`. A feature that
  logs nothing says so, and why, in its description. Keeping secrets out of
  everything Sammy records is specified once, in `keeping-secrets.feature`.
- Task issues follow step 3 too: branch from the issue, set In Progress,
  PR with `Closes #<n>`.
- Never commit on `master`; it only changes through merged PRs. GitHub
  branch protection enforces this (PR required, no force-push or deletion,
  admins included), and `.githooks/pre-commit` catches it earlier by
  rejecting commits on `master` locally. Each clone enables the hook once
  with `git config core.hooksPath .githooks`.
- Secret scanning with push protection is on: GitHub rejects pushes that
  contain recognisable keys or tokens.

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
- A step used by more than one feature goes in
  `tests/acceptance/steps/conftest.py`; a step used by one feature stays in
  that feature's `test_<name>.py`. Importing a step function into another
  file does not register it.
- `@scenario` on a `Scenario Outline` binds every `Examples` row, so also
  list the rows built so far with `@pytest.mark.built_examples({...}, ...)`
  (one dict of column values per row); `tests/acceptance/conftest.py`
  deselects the rest. Each row's PR adds its dict to the list.
- `tests/acceptance/drivers/` - the driver the steps talk to Sammy through,
  plus fakes such as the fake `ModelClient`. Import as `drivers.<module>`.
  The driver is the one seam: if the interface moves from CLI to web, only
  the driver changes, not the feature files.

### Unit tests
- Each agent's unit tests live in `agent/<name>/tests/`, and those for
  `libs/accounts/` in `libs/accounts/tests/`. Add them inside-out
  as the acceptance test exposes the need, not speculatively.
- Unit tests are implementation detail: they can be rewritten or deleted
  during refactoring. The "never weaken" rule applies to `tests/acceptance/`
  only.

### Running tests
- `uv run pytest` - everything.
- `uv run pytest tests/acceptance` - acceptance tests only.
- `uv run pytest agent` - agent unit tests only.
- `uv run pytest libs` - shared library unit tests only.
- `uv run pytest tools` - tooling tests only.
- Against PostgreSQL: set `SAMMY_TEST_DATABASE_URL` to a server the tests may
  create and drop databases on, then run the acceptance tests. Locally:
  ```
  podman run -d --rm --name sammy-test-postgres -e POSTGRES_USER=sammy \
    -e POSTGRES_PASSWORD=sammy-test -p 127.0.0.1:55432:5432 docker.io/library/postgres:17
  SAMMY_TEST_DATABASE_URL=postgresql+psycopg://sammy:sammy-test@127.0.0.1:55432/postgres \
    uv run pytest tests/acceptance
  ```
- CI (`.github/workflows/tests.yml`) runs every test on SQLite and the
  acceptance tests on PostgreSQL, for each PR and push to `master`.

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
  uv run cr-filter-operators session.sqlite cosmic-ray.toml
  uv run cosmic-ray exec cosmic-ray.toml session.sqlite
  uv run cr-report session.sqlite
  ```
  `cr-filter-git` ignores untracked files, so `git add` new files first or
  their mutants are all skipped.
- Two known-equivalent kinds of mutant are left out, so the survivors that
  remain are worth reading (both set in `cosmic-ray.toml`):
  - Turning `|` into another operator: on an `X | None` type hint it changes
    nothing, because Python 3.14 never evaluates annotations at runtime.
    `cr-filter-operators` skips these. The code rarely uses `|` for anything
    else; if it starts to, revisit this.
  - `libs/*/src/*/tables.py`: table definitions only describe the schema for
    building queries. The migrations create the schema, and a unit test
    keeps the two in step, so mutating them changes nothing at runtime.
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
- Scope: cosmic-ray only covers `agent/` (Python) for now. Add `libs` to
  `module-path` in `cosmic-ray.toml` as soon as the first package under
  `libs/` exists (every listed path must exist), otherwise login code goes
  unmutated. `web/` has no mutation coverage yet — out of scope
  until/unless a JS equivalent (Stryker) gets added.
- New scenarios or `Examples` rows to kill survivors are still acceptance
  tests, so they're proposed in the PR for a human to approve, never added
  silently. Once approved they go in via a spec PR (see Feature flow).

