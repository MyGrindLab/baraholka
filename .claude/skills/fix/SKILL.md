---
name: fix
description: Fix a bug end-to-end — reproduce with a failing test, patch, get to 100% green, have the tests human-verified, then open a reviewed PR. Accepts either a Jira issue key (reads the task via the Jira MCP) or a free-text bug description. Usage: /fix <task-number | description>. Stops at the open PR — approval and merge are the human's.
---

# /fix — bug task → reviewed PR

You orchestrate a bug fix. Two mandatory human gates (verify tests, approve PR); everything else runs autonomously.

The task: **$ARGUMENTS**  (either a Jira issue key like `PROJ-123`, or a free-text bug description)

## 1. Understand the bug
**If the argument looks like a Jira issue key** (e.g. `PROJ-123`): fetch it via the **atlassian** MCP — description, repro steps, expected vs. actual, comments — restate the bug, and move the issue to **In Progress**. Jira status updates in later steps apply.
**Otherwise** treat the argument as the bug description directly (no Jira). Skip all Jira status updates.
Create branch `fix/<short-slug>` (prefix the Jira key if there is one) — never work on main/master.

## 2. Reproduce & fix (subagents)
- **qa-tester** writes the smallest test that fails *because of this bug*, confirmed failing for the right reason. If it can't be reproduced, report that with what you tried before guessing — a fix without a repro is a guess.
- Find the **root cause** (state it in one sentence). qa-tester owns the fix and the proving test; if it needs backend/frontend domain code, hand that slice to **backend-go** / **backend-python** / **frontend-react** while qa keeps the failing→passing test.

## 3. Test & review — 100% green, then HUMAN-VERIFIED tests
- Run the new regression test (now passing) plus the **full suite to 100% green** — a hard gate; no failing/skipped tests.
- Inline self-review: fix is correct, targets the root cause (not the symptom), no security/data-safety regression.
- **STOP and hand the test code to the user** — the new regression test plus any changed tests, one-line intent each — and get confirmation before the PR. (Test code must be verified by a human.)

## 4. Push & create PR
Commit, push, `gh pr create`. If there's a Jira key, put it in the title (`[PROJ-123] fix: ...`) and body. Include: the bug, the root cause, the regression test added, and test results (100% green). The `@claude` GitHub Action reviews automatically; request a review if it doesn't fire. If there's a Jira key, move the issue to **In Review**.

## 5. Approval — ONLY the human
Stop at the open PR. Report the PR link and status. **You never approve or merge.**

## 6. Task status on merge
If the work came from a Jira task, it moves to **Done** on merge (GitHub↔Jira automation / follow-up run) — note this in your report. For a free-text bug there's nothing to update.

## Rules
- Input is either a Jira key or a free-text bug description. If it's a Jira key, read the task and write status back; if it's free text, skip Jira entirely.
- No fix ships without a regression test that would have caught the bug — that test is the deliverable, as much as the patch.
- Name the root cause; symptom-only patches are not acceptable.
- Two human gates are non-negotiable: tests verified before PR, PR approved before merge.
