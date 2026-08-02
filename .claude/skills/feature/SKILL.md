---
name: feature
description: Implement a feature end-to-end — architect designs and splits the work, implementer agents build it in Docker, tests go 100% green and get human-verified, then a reviewed PR with a changelog entry and an agent trace. Accepts either a Jira issue key (reads the task via the Jira MCP) or a free-text description. Usage: /feature <task-number | description>. Stops at the open PR — approval and merge are the human's.
---

# /feature — task → reviewed PR

You orchestrate a feature: **new behavior that doesn't exist yet.** The architect leads. The flow has two mandatory human gates (verify tests, approve PR); everything else runs autonomously.

> **`/feature` vs `/fix`** — `/feature` is architect-led: design first, then build. `/fix` is qa-led: reproduce and diagnose first, then hand a bug report to the implementer. If the request is "X is broken/wrong", use `/fix` instead.

The task: **$ARGUMENTS**  (either a Jira issue key like `PROJ-123`, or a free-text description)

> **Ping the human when you stop.** This flow runs long and unattended — the user has almost certainly walked away. Every time you stop and wait on them (an ambiguity in step 1, the test gate in step 4, the open PR in step 7), call the **PushNotification** tool with one line naming what you need: `"tests ready for review: 4 added, PROJ-123"` beats `"waiting for input"`. It reaches their phone if Remote Control is connected and self-suppresses when they're already watching the terminal, so the cost of sending is near zero and the cost of not sending is a run that sits idle for an hour. Permission prompts and idle waits are already covered by the `Notification` hook — you don't notify for those.

## 1. Understand the task
**If the argument looks like a Jira issue key** (e.g. `PROJ-123`): fetch it via the **atlassian** MCP — title, description, acceptance criteria, comments — restate your understanding, and move the issue to **In Progress**. Jira status updates in later steps apply.

> **Comments are not optional, and they are not free.** `getJiraIssue` omits them unless you ask: pass `fields: ["*all"]` (or the default set **plus `"comment"`**) and read `fields.comment.comments`. A description written at ticket-creation time is the *oldest* statement of the requirement — the thread underneath it is where scope gets cut, acceptance criteria get sharpened, and decisions get reversed. Read the comments **newest-first** and treat a later comment as **overriding** the description wherever they disagree.
>
> Fold the result into the restatement you show the user: what the ticket asked for, then **what the thread changed** ("description says X; PROJ-123 comment from 12 Mar narrows it to X-without-Y — building the narrowed version"). If a comment is ambiguous rather than contradictory, that's an ambiguity — ask, per the line below. Say explicitly when there were no comments, so a silent thread is never confused with an unread one.
**Otherwise** treat the argument as the task description directly (no Jira). Skip all Jira status updates.
Either way: if requirements are ambiguous, ask the user before coding. Create branch `feat/<short-slug>` (prefix the Jira key if there is one) — never work on main/master.

## 2. Design & split (architect)
Delegate to **architect** to produce the design and an ordered task list with an owner per task (`frontend-react`, `backend-go`, `backend-python`, `qa-tester`, `devops`). Route by directory:

| area | owner |
|------|-------|
| `frontend/` | `frontend-react` |
| `backend/` | `backend-go` or `backend-python` |
| `infrastructure/`, `Makefile`, Dockerfiles, CI | `devops` |
| tests at any level | `qa-tester` |

**Keep the architect's reasoning** — the approach, the contract, the rejected alternative. It goes in the trace in step 6; don't discard it after reading.

## 3. Build (implementer agents)
Delegate each task to its owner — parallel where the plan allows, sequenced for dependencies (backend contract before frontend integration). Work from their summaries to keep the main thread lean.

**Everything runs in Docker.** Agents use the root `Makefile` (`make up`, `make test-backend`, `make sh-frontend`) — never a host-installed `npm`/`go`/`pytest`. If a component needs a new dependency, service, or env var, that's a `devops` task against `infrastructure/docker-compose.yml` and the `Makefile`, not a host install.

## 4. Test & review — 100% green, then HUMAN-VERIFIED tests
- **qa-tester** writes/extends tests (unit + integration; E2E via the Playwright MCP against `make e2e`) and drives `make check` to **100% passing**. Hard gate: no failing or skipped tests.
- Do the inline self-review (correctness, security, data-safety, edge cases); send blocker/high issues back to the owning agent.
- **STOP and hand the test code to the user.** List every test added/changed with a one-line intent each, and ask the user to confirm the tests actually validate the requirement. Do not proceed to the PR until the user approves the tests. (Test code must be verified by a human.)

## 5. Changelog
Add one line to `CHANGELOG.md` under `[Unreleased]` → `Added` (or `Changed`), per `.claude/docs/run-report.md`. Commit it with the feature.

## 6. Push, PR, and agent trace
Commit, push, and `gh pr create`. If there's a Jira key, put it in the PR title (e.g. `[PROJ-123] ...`) and link it in the body. The body covers: what changed, the contract, test results (100% green), and the human test-verification note.

Then post the **agent trace** as a PR comment — the format and the ~50-line cap are in **`.claude/docs/run-report.md`**. For a feature the trace leads with the architect's plan and the work-split table.

Once the PR is complete — description written, changelog committed, trace posted — mark it ready for review by adding the label:

```
gh pr edit <pr-number> --add-label "ready_for_review"
```

That label is the signal that the PR is finished and awaiting review. Create the label once per repo if it doesn't exist (`gh label create ready_for_review`). If there's a Jira key, move the issue to **In Review**.

## 7. Approval — ONLY the human
Stop at the open PR. Report the PR link and the review/test status. **You never approve or merge** — that is exclusively the user's action.

## 8. Task status on merge
If the work came from a Jira task, it should move to **Done** when the PR merges (GitHub↔Jira automation, or a follow-up run) — note this in your report. For a free-text task there's nothing to update.

## Rules
- Input is either a Jira key or a free-text description. If it's a Jira key, read the task first and write status back so the board stays in sync; if it's free text, skip Jira entirely.
- All builds, tests, and runs happen **in containers**, through the `Makefile`. Host toolchains are not used.
- Two human gates are non-negotiable: (a) tests verified before PR, (b) PR approved before merge.
- 100% passing tests is required to reach the PR — no exceptions without explicit user override.
- Every PR carries both artifacts: the committed CHANGELOG line and the posted agent trace.
