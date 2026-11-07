# Sammy

Sammy is a self-hosted household agent. You log in and talk to a single **orchestrator**, which reads each request and passes it to the specialist agent best placed to handle it. By default every agent uses **local models served by Ollama**, so household data stays on the home network. An agent can **opt in** to a cloud frontier model such as Claude when a task needs more capability than the local models offer.

> **Status:** early scaffolding. The workspace, test tooling and conventions are in place. No agents are built yet.

## What Sammy is for

Sammy is meant to help with the running of the household: things like reviewing code in local projects, keeping an eye on the home network, keeping the household calendar up to date and notifying people when something needs attention. Each of these will be its own agent behind the orchestrator, added one at a time.

## Agents

Only agents that have been built are listed here.

| Agent | What it does |
|---|---|
| *(none yet; the orchestrator is first)* | |

## How it works

```mermaid
flowchart LR
    U[You<br/>CLI / web UI] -->|after login| O[Orchestrator]
    O -->|routes by message content| A[Specialist agents]
    O -.->|reads agent descriptions| D[(Database<br/>users, roles, agent registry)]
    O -.-> L[(Ollama VM<br/>local models)]
    A -.-> L
    A -.->|opt-in| F[(Frontier LLM<br/>e.g. Claude)]
```

- **User login.** People log in before they can talk to Sammy. User accounts are stored in Sammy's database, with passwords kept only as salted hashes.
- **Roles and permissions.** What each person can do comes from their roles. A role is a named set of permissions, such as managing users, viewing or managing the agent list, or talking to a particular agent. A person can hold several roles and gets everything those roles allow. New users start with none, so access is always given on purpose. The built-in `admin` role can do everything and can't be changed. The orchestrator only routes a request to agents the person is allowed to use.
- **SQLite or PostgreSQL.** `SAMMY_DATABASE_URL` chooses the database: a local SQLite file (`sqlite:///path/to/sammy.sqlite`) or an existing PostgreSQL server (`postgresql+psycopg://user:password@host/database`). Sammy creates and updates its tables itself when it starts.
- **LLM-based routing.** Each agent's name and description are stored in a database. The orchestrator gives a local model the user's message and these descriptions, and asks it to pick the best agent. There are no hand-written keyword rules, so adding an agent means registering it, not editing routing logic.
- **One model interface, many backends.** Agents depend on a small `ModelClient` protocol, not on a specific provider. Ollama is the default implementation. A frontier-model client (for example Anthropic's API) implements the same protocol, so switching an agent to the cloud is a configuration change, not a code change.
- **Model per agent.** Each agent chooses its own model through configuration. For example, a small, fast model can handle routing while a larger one handles heavier tasks.
- **Local by default.** Cloud models are never used implicitly. An agent uses one only when it is explicitly configured to and an API key is present.
- **Monolith first.** Agents are Python packages imported by whichever process runs them (a CLI now, the web backend later), not separately deployed services. They will be split out only when something concrete requires it.

## Infrastructure

Sammy runs on a home Proxmox host, alongside the services it depends on:

| VM | Role |
|---|---|
| **Ollama** | Serves the local models. Every local-model agent calls it over the LAN. |
| **Sammy** | Runs the orchestrator, the agents and (eventually) the web UI. |

## Repository layout

This is a [uv](https://docs.astral.sh/uv/) workspace with a single shared lockfile and virtual environment at the root.

```
agent/<name>/         one package per agent (orchestrator-agent first)
  tests/              that agent's unit tests
libs/accounts/        users, roles and login
  tests/              unit tests for accounts
cli/                  the sammy command: starts Sammy (settings, logging, database, services)
  tests/              unit tests for the entry point
web/                  from-scratch web UI and server (later)
tests/acceptance/
  features/           Gherkin .feature files, written in natural language
  steps/              pytest-bdd step definitions
  drivers/            test doubles and the driver the tests talk to Sammy through
tools/                repo tooling (e.g. creating issues from feature files)
  tests/              unit tests for the tooling
.githooks/            git hooks (pre-commit blocks commits on master)
cosmic-ray.toml       mutation-testing config
CLAUDE.md             build conventions (ATDD workflow, testing rules)
```

## Getting started

Requirements: Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```sh
git config core.hooksPath .githooks   # once per clone: blocks commits on master
uv sync                        # create .venv and install the workspace plus dev tools
uv run pytest                  # run all tests
uv run pytest tests/acceptance # acceptance tests only
uv run pytest agent            # agent unit tests only
uv run pytest libs             # shared library unit tests only
uv run pytest cli              # entry-point unit tests only
uv run pytest tools            # tooling tests only
```

To create Sammy's database, or bring it up to date, point `SAMMY_DATABASE_URL` at it (in the environment or a local `.env` file) and run:

```sh
SAMMY_DATABASE_URL=sqlite:///sammy.sqlite uv run sammy migrate
```

Logs go to `logs/sammy.log` (rotated daily); `SAMMY_LOG_DIR`, `SAMMY_LOG_LEVEL` and `SAMMY_LOG_RETENTION_DAYS` change that.

The tests use throwaway SQLite databases. To run the acceptance tests against PostgreSQL as well, start a disposable server and point `SAMMY_TEST_DATABASE_URL` at it:

```sh
podman run -d --rm --name sammy-test-postgres -e POSTGRES_USER=sammy \
  -e POSTGRES_PASSWORD=sammy-test -p 127.0.0.1:55432:5432 docker.io/library/postgres:17
SAMMY_TEST_DATABASE_URL=postgresql+psycopg://sammy:sammy-test@127.0.0.1:55432/postgres \
  uv run pytest tests/acceptance
```

CI runs both on every pull request.

To add a new agent, run from the repo root:

```sh
uv init --package agent/<name>   # registers it as a workspace member
uv sync
```

## Development approach

Sammy is built **acceptance-test first**. Every behaviour starts as a Given/When/Then scenario written in natural language, not in terms of the code. The scenario must fail first, and is then made to pass with the smallest reasonable change. LLM calls are faked at the `ModelClient` boundary, so the suite is fast and deterministic and doesn't need the Ollama VM running.

Each agent also has its own unit tests, kept separate from the acceptance tests.

**Mutation testing** with [cosmic-ray](https://github.com/sixty-north/cosmic-ray) checks that the acceptance scenarios actually pin the behaviour down. A surviving mutant is treated as a missing scenario.

The full rules and commands are in [CLAUDE.md](CLAUDE.md).
