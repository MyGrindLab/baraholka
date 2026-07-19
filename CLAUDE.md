# <PROJECT_NAME>

> Base full-stack repo. After forking, fill in the blanks below and delete this line.
> Keep this file SMALL — it loads on every message. Facts and pointers only; workflows live in `.claude/skills/`, role knowledge in `.claude/agents/`.

## Stack
- Backend: <Go (chi/gin) | Python (FastAPI/Django)> — remove the one you don't use
- Frontend: <React + TypeScript (Vite/Next)>
- Database: <Postgres | ...>
- Infra: <Kubernetes + Helm, Argo CD> — deploy target

## Conventions
- Backend test/lint: `<pytest / ruff / mypy>` or `<go test ./... / go vet>`
- Frontend test/lint: `<vitest / eslint / tsc>`
- Never commit directly to `main` — always a PR.

## Agents (mixture of experts, in `.claude/agents/`)
- `architect` — designs and distributes work across the agents
- `backend-go`, `backend-python` — backend logic
- `frontend-react` — frontend logic
- `qa-tester` — writes tests + fixes bugs (Playwright MCP for E2E)
- `devops` — infra, CI/CD, k8s, Argo GitOps

## Workflows (`.claude/skills/`)
Both accept a **Jira key** (reads the task via Jira MCP, writes status back) **or a free-text description**, then run: understand → plan & code (subagents) → 100% green + **human-verified tests** → reviewed PR. Approval/merge is human-only.
- `/feature <task-number | description>` — e.g. `/feature PROJ-123` or `/feature add a health endpoint`
- `/fix <task-number | description>` — e.g. `/fix PROJ-124` or `/fix login button crashes on empty email`

## MCP servers (`.mcp.json`)
- **atlassian** — Jira/Confluence. Run `/mcp` once per fork to authenticate (OAuth, no secrets in repo).
- **playwright** — browser automation for E2E checks.
