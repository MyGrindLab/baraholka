# app-base

A **base repo you fork** to start a new full-stack project with the Claude Code setup already baked in. The config lives in `.claude/` + `.mcp.json` and travels with every fork — no plugin, no install step. Fork it, fill in `CLAUDE.md`, and you immediately have `/feature`, `/fix`, and the Jira + Playwright MCP servers.

## How to use it

1. **Fork / "Use this template"** on GitHub → new project repo.
2. Clone it and open Claude Code in the repo.
3. Fill in the `<...>` placeholders in `CLAUDE.md` (stack, framework, DB).
4. Run `/mcp` once to authenticate Jira (OAuth).
5. Run `/install-github-app` once to enable the `@claude` GitHub Action (installs the app + `ANTHROPIC_API_KEY` secret).
6. Start building: `/feature add a health endpoint`.

That's the whole setup. Everything below is what you get.

## Mixture of experts — why it stays cheap on tokens

| Layer | In context | Cost | Holds |
|-------|-----------|------|-------|
| `CLAUDE.md` | always | high | tiny project facts only |
| skills (`/feature`, …) | just the 1-line description until invoked | ~free | workflows |
| subagents (experts) | isolated window; only a summary returns to the main thread | cheap | role knowledge |

Roles live in **subagents**, not the main prompt — so having several experts costs almost nothing until one runs. Each agent's `model:` is tunable (bump the architect to Opus for hard designs, drop cheap agents to Haiku).

## What's inside `.claude/`

**Skills (your slash commands)** — each takes **a Jira key _or_ a free-text description**:
- `/feature <task-number | description>` — plan & code → 100% green + human-verified tests → reviewed PR
- `/fix <task-number | description>` — reproduce → patch → 100% green + human-verified tests → reviewed PR

Each runs: **1.** understand the task (Jira MCP if given a key, else the description) → **2.** subagents plan & code (architect, backend, frontend, qa, devops) → **3.** test to 100% green, then *you verify the test code* → **4.** push + open PR (auto-reviewed by the `@claude` action) → **5.** *you* approve/merge → **6.** Jira status updates (when there's a linked task).

**Subagents (experts)**
- `architect` — designs the app/feature and distributes tasks across the agents
- `backend-go` · `backend-python` — backend logic
- `frontend-react` — frontend logic (React + TypeScript)
- `qa-tester` — writes tests (unit/integration/E2E via Playwright MCP) and fixes bugs
- `devops` — infra, CI/CD, Kubernetes/Helm, Argo GitOps

**MCP servers** (`.mcp.json`)
- `atlassian` — Jira/Confluence over OAuth (run `/mcp` once per fork; no secrets in the repo)
- `playwright` — browser automation for E2E checks

**Hooks** (`.claude/settings.json` + `.claude/hooks/`) — block direct pushes to main and destructive commands; auto-format edited files.

**GitHub Action** (`.github/workflows/claude.yml`) — pre-wired `anthropics/claude-code-action@v1`. Mention **`@claude`** in any issue or PR comment and it answers questions or implements changes. Needs the one-time `/install-github-app` (or an `ANTHROPIC_API_KEY` repo secret).

## The autonomy contract
`/feature` and `/fix` run autonomously *between* two human gates: **(1)** you verify the test code before the PR is opened, and **(2)** you approve/merge the PR. Everything in between — reading the task, planning, coding, getting to 100% green, opening the auto-reviewed PR, updating Jira — is hands-off. Nothing lands on `main` without you.

## Extending later
Adding another expert (e.g. `mobile`, `data-engineer`) is just dropping a new `agents/<name>.md`; the architect will distribute tasks to it and the skills will delegate. Per fork, delete the backend agent you don't use (Go *or* Python).
