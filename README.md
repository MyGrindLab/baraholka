# app-base

A **base repo you fork** to start a new full-stack project with the Claude Code setup already baked in. The config lives in `.claude/` + `.mcp.json` and travels with every fork — no plugin, no install step. Fork it, run `/init-project`, and you immediately have `/feature`, `/fix`, a containerized dev environment, and the Jira + Playwright MCP servers.

## How to use it

1. **Fork / "Use this template"** on GitHub → new project repo.
2. Clone it and open Claude Code in the repo. You need **Docker** — nothing else.
3. Run `/mcp` once to authenticate Jira (OAuth).
4. Run `/init-project <link to your project description page>` — reads the doc and fills in `CLAUDE.md`, `README.md`, a `CLAUDE.md` per component, and the `Makefile`/compose placeholders. A Jira key (`/init-project PROJ`) or a one-sentence description works too.
5. Run `/install-github-app` once to enable the `@claude` GitHub Action (installs the app + `ANTHROPIC_API_KEY` secret).
6. Start building: `/feature <your first task>`. The first feature is usually scaffolding a component — `devops` fills in `infrastructure/` and the matching `Makefile` targets, and from then on `make up` runs the stack.

That's the whole setup. Everything below is what you get.

## Structure

```
frontend/      UI — required                    → frontend-react
backend/       API + domain logic               → backend-go | backend-python
infrastructure/         docker-compose + Dockerfiles     → devops
Makefile       one entry point for everything   → devops
CHANGELOG.md   one line per feature/fix
```

The directories and the `Makefile` target names are the agreed **structure**; the components themselves are scaffolded later, per project. Nothing here presumes a framework — anything meant to be filled in later ships as a **template**, with placeholders rather than a plausible-looking guess.

**Everything runs in Docker.** No node, go, or python on your machine — the `Makefile` shells into containers for every build, test, lint, and migration. Each component stays independently runnable (`make up-frontend`, `make up-backend`), and `infrastructure/` + the `Makefile` are `devops`-owned: other agents *request* a new dependency or service, they never install one on the host. A change that only works outside the container is a broken change.

```
make help          # list the interface
make up            # run the whole stack
make test-backend  # one component's suite, in its container
make check         # lint + test — the pre-PR gate, identical to CI
```

The Makefile ships as a skeleton: `make help` already lists the full interface, and every unfilled target exits with a pointer instead of pretending to work. `devops` fills in the bodies when `infrastructure/` is scaffolded.

## Mixture of experts — why it stays cheap on tokens

| Layer | In context | Cost | Holds |
|-------|-----------|------|-------|
| root `CLAUDE.md` | always | high | only facts true for the **whole** repo |
| `<component>/CLAUDE.md` | only while working in that component | cheap | its stack + make targets |
| skills (`/feature`, …) | just the 1-line description until invoked | ~free | workflows |
| subagents (experts) | isolated window; only a summary returns to the main thread | cheap | role knowledge |

**The split.** Because the root file is paid for on every message, it holds only what's true everywhere: the layout table, the Docker-only rule, `make check`, the PR rule. Once a component is scaffolded, its framework and test commands go in `frontend/CLAUDE.md` / `backend/CLAUDE.md`, which load only when Claude touches that subtree. Rule of thumb: **if a fact is false for any component, push it down.** `/init-project` does this split for you.

Roles live in **subagents**, not the main prompt — so having several experts costs almost nothing until one runs. Each agent's `model:` is tunable (bump the architect to Opus for hard designs, drop cheap agents to Haiku).

## What's inside `.claude/`

**Skills (your slash commands)** — each takes **a Jira key _or_ a free-text description**:
- `/feature <task-number | description>` — new behavior → 100% green + human-verified tests → reviewed PR
- `/fix <task-number | description>` — broken behavior → 100% green + human-verified tests → reviewed PR
- `/init-project <confluence-url | PROJ | description>` — run once per fork. **Paste the link to your project description page** (Confluence page, tiny `/wiki/x/` link, or space overview) and it reads the doc — following one level of child pages when the page is an index — for purpose, scope, component breakdown, and intended stack. Give it a Jira key instead (or as well) and it adds the project's components and issue history. It checks all of that against what's actually in the repo, then writes the docs, fills the `Makefile`/compose placeholders, and drops the template parts you don't use. Read-only on Jira/Confluence; shows you the diff before committing, and leaves anything it can't verify as an open question rather than inventing it.

Both run: **1.** understand the task (Jira MCP if given a key, else the description) → **2.** subagents work in containers → **3.** test to 100% green, then *you verify the test code* → **4.** changelog line + push + open PR with an agent trace, labeled `ready_for_review` → **5.** *you* approve/merge → **6.** Jira status updates (when there's a linked task).

### `/feature` vs `/fix` — different leads, on purpose

|  | `/feature` — **architect-led** | `/fix` — **qa-led** |
|--|-------------------------------|---------------------|
| starts with | design & task split | reproduction & diagnosis |
| then | implementers build to the contract | qa hands a **bug report** to the owning implementer |
| qa-tester's job | write the tests | prove the bug, write the failing test, verify the fix |
| who writes the patch | the implementer agent | the implementer agent — **never qa** |

In `/fix`, nobody writes a patch until qa-tester has reproduced the bug in the containers and produced a report the implementer doesn't have to re-investigate: symptom, exact repro steps, expected vs actual, **root cause at file:line**, the failing test and how to run it, trimmed evidence, and blast radius. The implementer fixes the root cause and doesn't touch that test — it's the contract between them. Diagnosis and repair stay separate jobs, so the test that proves the fix was written by someone who hadn't yet committed to a fix. If it can't be reproduced, that's reported as a finding, not papered over with a guess.

**Subagents (experts)**
- `architect` — designs the app/feature and distributes tasks across the agents
- `backend-go` · `backend-python` — backend logic (`backend/`)
- `frontend-react` — frontend logic (`frontend/`, React + TypeScript)
- `qa-tester` — writes tests (unit/integration/E2E via Playwright MCP); reproduces and diagnoses bugs, then hands them off
- `devops` — `Makefile` + `infrastructure/`, CI/CD, Kubernetes/Helm, Argo GitOps

**MCP servers** (`.mcp.json`)
- `atlassian` — Jira/Confluence over OAuth (run `/mcp` once per fork; no secrets in the repo)
- `playwright` — browser automation for E2E checks

**Hooks** (`.claude/settings.json` + `.claude/hooks/`) — block direct pushes to main and destructive commands; auto-format edited files.

**GitHub Action** (`.github/workflows/claude.yml`) — pre-wired `anthropics/claude-code-action@v1`. Mention **`@claude`** in any issue or PR comment and it answers questions or implements changes. Needs the one-time `/install-github-app` (or an `ANTHROPIC_API_KEY` repo secret).

## What every run leaves behind

Two artifacts per `/feature` or `/fix`, spec'd in `.claude/docs/run-report.md`:

- **A `CHANGELOG.md` line** (committed) under `[Unreleased]` — the user-visible change, written for release notes: *"Login no longer crashes on an empty email"*, not *"add null check in validateEmail()"*.
- **An agent trace** posted as a PR comment (not committed — traces describe one run, and committing them turns the repo into a log). Capped at ~50 lines, no diffs: the task as interpreted, the architect's plan *or* qa's diagnosis, a **who-changed-what table** (agent → files → why), the containerized commands that verified it, and any non-obvious decisions or open items.

The point of the trace is that a reviewer can see **how** the change was produced — who analyzed what, how it was split, who touched which files — without re-deriving it from the diff. It's required to be honest: a reproduction that failed or a task handed back and redone gets recorded, because a trace where everything always went perfectly is one nobody reads twice.

## The autonomy contract
`/feature` and `/fix` run autonomously *between* two human gates: **(1)** you verify the test code before the PR is opened, and **(2)** you approve/merge the PR. Everything in between — reading the task, planning, coding, getting to 100% green, opening the auto-reviewed PR, updating Jira — is hands-off. Nothing lands on `main` without you.

## Extending later
Adding another expert (e.g. `mobile`, `data-engineer`) is just dropping a new `agents/<name>.md`; the architect will distribute tasks to it and the skills will delegate. Give it a home directory and a `Makefile` target so it stays inside the container rule. Per fork, delete the backend agent you don't use (Go *or* Python).
