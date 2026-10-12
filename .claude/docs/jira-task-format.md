# Jira issue format

The one format for every issue Claude creates — by `/jira-task`, `/analyze-project`, or `/prod-check`. Identifiers come from `.claude/docs/project.md`.

An issue is written for **the person who picks it up cold**, possibly in a month, possibly from a phone. If they'd have to ask a question before starting, the issue isn't finished.

## Fields

| field | rule |
|-------|------|
| **Project** | the shared project key from `project.md` |
| **Issue type** | `Bug` (existing behavior is wrong) · `Story` (new user-visible behavior) · `Task` (tech debt, infra, refactor, docs — no user-visible change). Use the type names the project actually has (`getJiraProjectIssueTypesMetadata`) — map, don't invent. The default Kanban (`KAN`) template often has only `Task`/`Epic`/`Subtask`: then a Bug is filed as `Task` + label `bug`, a Story as `Task` + label `story`, and the template below is used unchanged |
| **Summary** | ≤ 80 chars, imperative for Story/Task (`Add rate limit to /login`), symptom for Bug (`Login returns 500 on empty email`). No `[project]` prefix — the label does that job |
| **Labels** | always: the **project label** + `claude-created`. Plus one **area** label (`area-frontend` · `area-backend` · `area-infra` · `area-docs`) and one **kind** label when it applies (`security` · `performance` · `tech-debt` · `test-gap` · `ux` · `a11y`). Plus the **source** label of the skill that filed it (`from-analyzer` · `from-prod-check`). Lowercase, hyphens, no spaces |
| **Component** | the project component from `project.md`, if one is configured |
| **Priority** | from severity, below. Only if the project has a priority field |
| **Parent** | the epic from `project.md`, if configured, or the one the user named |
| **Assignee** | leave unassigned unless asked |

Fields beyond these (story points, sprint, fix version, custom fields) — set them only if `getJiraIssueTypeMetaWithFields` marks them **required**, and then ask for the value rather than guessing it.

## Severity → priority

| severity | means | priority |
|----------|-------|----------|
| critical | data loss, security hole, prod down, payment broken | Highest |
| high | a core journey is broken or wrong for many users; no workaround | High |
| medium | broken edge case, or core journey degraded with a workaround | Medium |
| low | cosmetic, minor tech debt, nice-to-have | Low |

## Description templates

Markdown (the MCP converts it). Keep the headings, drop a section only when it truly doesn't apply. Reference code as `path/to/file.go:88` and link the repo commit when one is relevant.

### Bug
```markdown
## Summary
<one or two sentences: what's wrong and who it hits>

## Steps to reproduce
1. <exact step, from a clean state>
2. ...

## Expected
<one line>

## Actual
<one line>

## Environment
<prod / local stack · URL · browser + viewport · account type · build/commit if known>

## Evidence
<trimmed console error / failed request (method, URL, status) / log line / stack frames>
<screenshot attached or described>

## Suspected cause
<file:line and why — or "not investigated">

## Acceptance criteria
- [ ] <the repro above no longer fails>
- [ ] A regression test covers it
```

### Story
```markdown
## Context
<why this matters — the problem, not the solution>

## User story
As a <role>, I want <capability>, so that <outcome>.

## Acceptance criteria
- [ ] Given <state>, when <action>, then <result>
- [ ] ...

## Out of scope
- <what this deliberately does not cover>

## Notes
<constraints, links to designs/docs, affected areas: `frontend/...`, `backend/...`>
```

### Task
```markdown
## Context
<why — what's wrong or costly today>

## Goal
<the end state in one or two sentences>

## Scope
- <concrete change, with paths: `backend/api/user.go`>
- ...

## Done when
- [ ] <verifiable outcome — a passing `make check`, a removed file, a metric>

## Risks / notes
<anything that could bite — migrations, breaking changes, ordering>
```

## Footer — always last
```markdown
---
🤖 Created by Claude (`/<skill>`) from repo `<repo name>` @ `<short sha>`.
```

## Before creating — duplicate check
Search with the project JQL plus words from the summary — open issues **and descoped ones**:
`project = KAN AND labels = <project-label> AND (statusCategory != Done OR status = Descope) AND text ~ "<2-4 key words>"`
- **Match in `Descope`** → the human already declined this. Don't create, don't comment; report it as `descoped: KAN-123`. The one exception is new evidence of a **critical** problem (security, data loss, prod down) — then tell the user directly and let them decide, still without touching the issue.
- **Clear duplicate** (open) → don't create; add a comment to the existing issue with any new evidence and report its key.
- **Related** → create, and link it (`createIssueLink`, "relates to").
- Searching without the project label would match other repos' issues in the shared project — always include it.

## After creating
Re-read the issue (`getJiraIssue`) and confirm the labels and parent actually landed — a field the screen doesn't accept is dropped silently. Report `KEY — summary — URL`.
