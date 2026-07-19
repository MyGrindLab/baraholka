---
name: feature
description: Implement a feature end-to-end — plan & code with subagents, test to 100% green, get the tests human-verified, then open a reviewed PR. Accepts either a Jira issue key (reads the task via the Jira MCP) or a free-text description. Usage: /feature <task-number | description>. Stops at the open PR — approval and merge are the human's.
---

# /feature — task → reviewed PR

You orchestrate a feature. The flow has two mandatory human gates (verify tests, approve PR); everything else runs autonomously.

The task: **$ARGUMENTS**  (either a Jira issue key like `PROJ-123`, or a free-text description)

## 1. Understand the task
**If the argument looks like a Jira issue key** (e.g. `PROJ-123`): fetch it via the **atlassian** MCP — title, description, acceptance criteria, comments — restate your understanding, and move the issue to **In Progress**. Jira status updates in later steps apply.
**Otherwise** treat the argument as the task description directly (no Jira). Skip all Jira status updates.
Either way: if requirements are ambiguous, ask the user before coding. Create branch `feat/<short-slug>` (prefix the Jira key if there is one) — never work on main/master.

## 2. Plan & code (subagents)
Delegate to **architect** to design and produce an ordered task list with an owner per task (`backend-go`, `backend-python`, `frontend-react`, `qa-tester`, `devops`). Then delegate each task to its owner — parallel where the plan allows, sequenced for dependencies (backend contract before frontend integration). Work from their summaries to keep the main thread lean.

## 3. Test & review — 100% green, then HUMAN-VERIFIED tests
- **qa-tester** writes/extends tests (unit + integration; E2E via the Playwright MCP) and drives the suite to **100% passing**. This is a hard gate: you may not proceed with any failing or skipped test.
- Do the inline self-review (correctness, security, data-safety, edge cases); send blocker/high issues back to the owning agent.
- **STOP and hand the test code to the user.** List every test added/changed with a one-line intent each, and ask the user to confirm the tests actually validate the requirement. Do not proceed to the PR until the user approves the tests. (Test code must be verified by a human.)

## 4. Push & create PR
Commit, push, and `gh pr create`. If there's a Jira key, put it in the PR title (e.g. `[PROJ-123] ...`) and link it in the body. Include: what changed, the contract, test results (100% green), and the human test-verification note. The `@claude` GitHub Action reviews the PR automatically; if it doesn't fire, request a review. If there's a Jira key, move the issue to **In Review**.

## 5. Approval — ONLY the human
Stop at the open PR. Report the PR link and the review/test status. **You never approve or merge** — that is exclusively the user's action.

## 6. Task status on merge
If the work came from a Jira task, it should move to **Done** when the PR merges (GitHub↔Jira automation, or a follow-up run) — note this in your report. For a free-text task there's nothing to update.

## Rules
- Input is either a Jira key or a free-text description. If it's a Jira key, read the task first and write status back so the board stays in sync; if it's free text, skip Jira entirely.
- Two human gates are non-negotiable: (a) tests verified before PR, (b) PR approved before merge.
- 100% passing tests is required to reach the PR — no exceptions without explicit user override.
