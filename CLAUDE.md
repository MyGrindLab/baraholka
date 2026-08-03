# <PROJECT_NAME>

> Base full-stack repo. After forking, run `/init-project` (or fill in the blanks below) and delete this line.
> Keep this file SMALL — it loads on every message. Only facts true for the **whole** repo; per-package detail goes in that package's own `CLAUDE.md`, workflows in `.claude/skills/`, role knowledge in `.claude/agents/`.

## Repo layout — fixed
| path | what lives there | owner agent |
|------|------------------|-------------|
| `frontend/` | UI — **required** | `frontend-react` |
| `backend/` | API + domain logic | `<backend-go \| backend-python>` |
| `infrastructure/` | docker-compose + Dockerfiles; each component runs separately | `devops` |
| `Makefile` | the one entry point for everything (root) | `devops` |
| `CHANGELOG.md` | one line per feature/fix, added before the PR | whoever runs the skill |

**Nothing is scaffolded yet.** The directories and the `Makefile` target names are the agreed structure; the contents come later. Files meant to be filled in later ship as **templates** — placeholders and `<...>`, never a plausible-looking guess. When a component is built, its stack and commands go in its own `<component>/CLAUDE.md`, never here.

## Conventions — Docker only
- **Nothing runs on the host.** Every build, test, lint, and migration goes through the root `Makefile`, which shells into containers. No local node/go/python toolchain is used — if a command isn't a make target, ask `devops` to add one.
- `make help` lists the interface · `make up` runs the stack · `make check` is the pre-PR gate (lint + test). The bodies are `$(TODO)` placeholders until `devops` fills them in.
- `infrastructure/` and the `Makefile` are `devops`-owned — other agents request changes there, they don't edit them.
- Every feature/fix adds a `CHANGELOG.md` line and posts an agent trace to the PR — see `.claude/docs/run-report.md`.
- Never commit directly to `main` — always a PR.

## Agents (mixture of experts, in `.claude/agents/`)
- `architect` — designs and distributes work across the agents
- `backend-go`, `backend-python` — backend logic
- `frontend-react` — frontend logic
- `qa-tester` — writes tests; reproduces & diagnoses bugs, then hands a report to an implementer (Playwright MCP for E2E)
- `devops` — `Makefile` + `infrastructure/`, CI/CD, k8s, Argo GitOps

## Workflows (`.claude/skills/`)
`/feature` and `/fix` accept a **Jira key** (reads the task via Jira MCP, writes status back) **or a free-text description**, and both end at: 100% green → PR + changelog line + agent trace. **They run unattended**: questions and judgment calls become Jira comments and the run continues under a stated assumption, rather than halting for input. Approval/merge is human-only.
- `/feature <task-number | description>` — **architect-led**: design → split → build → test. New behavior.
- `/fix <task-number | description>` — **qa-led**: reproduce → diagnose → hand the bug report to the implementer who patches it. Broken behavior.
- `/init-project <confluence-url | PROJ | description>` — **run once after forking**: reads the project description (a Confluence doc link is the best input) and writes this file + `README.md` + per-package `CLAUDE.md`s. Read-only on Jira/Confluence.

## MCP servers (`.mcp.json`)
- **atlassian** — Jira/Confluence. Run `/mcp` once per fork to authenticate (OAuth, no secrets in repo).
- **playwright** — browser automation for E2E checks.
