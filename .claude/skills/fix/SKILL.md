---
name: fix
description: Fix a bug end-to-end — qa-tester reproduces and diagnoses it and hands a full bug report to the owning implementer agent, who patches it; then 100% green, human-verified tests, and a reviewed PR with a changelog entry and an agent trace. Accepts either a Jira issue key (reads the task via the Jira MCP) or a free-text bug description. Usage: /fix <task-number | description>. Stops at the open PR — approval and merge are the human's.
---

# /fix — bug → reviewed PR

You orchestrate a bug fix: **existing behavior that's wrong.** Two mandatory human gates (verify tests, approve PR); everything else runs autonomously.

> **`/fix` vs `/feature`** — `/fix` is **qa-led**: qa-tester finds and proves the bug *before* anyone writes a patch, then hands it off. `/feature` is architect-led. The architect is only involved here if the root cause turns out to be a design problem (see step 3).

The task: **$ARGUMENTS**  (either a Jira issue key like `PROJ-123`, or a free-text bug description)

> **Ping the human when you stop.** This flow runs long and unattended — the user has almost certainly walked away. Every time you stop and wait on them (**an unreproducible bug in step 2**, the test gate in step 4, the open PR in step 7), call the **PushNotification** tool with one line naming what you need: `"can't reproduce PROJ-123 — need a repro or env detail"` beats `"waiting for input"`. It reaches their phone if Remote Control is connected and self-suppresses when they're already watching the terminal. Permission prompts and idle waits are already covered by the `Notification` hook — you don't notify for those.

## 1. Understand the report
**If the argument looks like a Jira issue key**: fetch it via the **atlassian** MCP — description, repro steps, expected vs. actual, comments, attachments — restate the bug, and move the issue to **In Progress**. Jira status updates in later steps apply.

> **Comments are not optional, and they are not free.** `getJiraIssue` omits them unless you ask: pass `fields: ["*all"]` (or the default set **plus `"comment"`**) and read `fields.comment.comments`. On a bug ticket the thread is usually worth more than the description — it's where the reporter adds the *actual* repro ("only happens when logged out"), narrows the affected version, attaches the stack trace, or notes that half the report was user error. Read the comments **newest-first** and treat a later comment as **overriding** the description wherever they disagree.
>
> Fold the result into the restated bug and hand it to **qa-tester in step 2** — a repro step that's only in comment #4 is the difference between reproducing the bug and reporting it unreproducible. Say explicitly when there were no comments, so a silent thread is never confused with an unread one.
**Otherwise** treat the argument as the bug description directly (no Jira). Skip all Jira status updates.
Create branch `fix/<short-slug>` (prefix the Jira key if there is one) — never work on main/master.

## 2. Investigate & reproduce (qa-tester) — before any patch
**qa-tester owns this phase and does not fix anything in it.** Its job is to turn a complaint into a proven, precisely located defect:

- Bring the stack up with `make up` and reproduce the bug **in the containers**, not on a host. Use the Playwright MCP for UI bugs, container logs (`make logs S=backend`) for server-side ones.
- Write the **smallest failing test**, confirmed failing *because of the bug* and not a setup error.
- Find the **root cause** — the specific code path, not the symptom.

If it can't be reproduced, **stop and report** what was tried, what was observed instead, and what's needed (a real repro, an env detail, a data sample). Do not guess a patch. An unreproducible bug is a finding, not a failure.

## 3. Hand off the bug report → implementer
qa-tester hands the owning agent — `frontend-react` (`frontend/`), `backend-go`/`backend-python` (`backend/`), or `devops` (`infrastructure/`, `Makefile`, CI) — a **complete report**. The implementer must not have to re-investigate:

```markdown
**Symptom** — what the user sees, and where (which service/container, which URL/endpoint).
**Reproduction** — exact steps from `make up` to failure, incl. the data/input used.
**Expected vs actual** — one line each.
**Root cause** — the code path and why it's wrong. `backend/api/user.go:88 — email is
dereferenced before the empty check, so an empty form field panics.`
**Failing test** — path + how to run it (`make test-backend`), and what it asserts.
**Evidence** — the stack trace / log line / console error. Trimmed to the relevant frames.
**Blast radius** — other call sites with the same flaw, or "none found".
**Suggested fix** — optional, and explicitly the implementer's call to accept or reject.
```

The implementer patches the **root cause**, not the symptom, and doesn't touch the failing test — that test is the contract between them. Work in Docker via the `Makefile`.

**If the root cause is a design flaw** (the fix needs a contract or schema change, or spans several components), pull in **architect** for that slice before patching — but keep qa's failing test as the definition of done.

## 4. Verify — 100% green, then HUMAN-VERIFIED tests
- qa-tester confirms the once-failing test now passes **for the right reason**, then runs `make check` to **100% green**. Hard gate: no failing or skipped tests.
- Inline self-review: the patch targets the root cause, covers the blast radius, and introduces no security/data-safety regression.
- **STOP and hand the test code to the user** — the new regression test plus any changed tests, one-line intent each — and get confirmation before the PR. (Test code must be verified by a human.)

## 5. Changelog
Add one line to `CHANGELOG.md` under `[Unreleased]` → `Fixed`, per `.claude/docs/run-report.md`. Describe the bug as the user experienced it, not the patch. Commit it with the fix.

## 6. Push, PR, and agent trace
Commit, push, `gh pr create`. If there's a Jira key, put it in the title (`[PROJ-123] fix: ...`) and body. The body covers: the bug, the root cause, the regression test added, and test results (100% green).

Then post the **agent trace** as a PR comment — format and ~50-line cap in **`.claude/docs/run-report.md`**. For a fix the trace leads with qa's **Diagnosis** (symptom → reproduction → root cause) instead of an architect plan, then the handoff and who patched what.

Once the PR is complete — description written, changelog committed, trace posted — mark it ready for review by adding the label:

```
gh pr edit <pr-number> --add-label "ready_for_review"
```

That label is the signal that the PR is finished and awaiting review. Create the label once per repo if it doesn't exist (`gh label create ready_for_review`). If there's a Jira key, move the issue to **In Review**.

## 7. Approval — ONLY the human
Stop at the open PR. Report the PR link and status. **You never approve or merge.**

## 8. Task status on merge
If the work came from a Jira task, it moves to **Done** on merge (GitHub↔Jira automation / follow-up run) — note this in your report. For a free-text bug there's nothing to update.

## Rules
- **Diagnosis and repair are separate jobs.** qa-tester proves the bug and writes the report; an implementer agent writes the patch. Never let the same step both discover and fix — the failing test has to exist before the patch does.
- No fix ships without a regression test that would have caught the bug — that test is the deliverable, as much as the patch.
- Reproduce in containers via the `Makefile`; never debug against a host toolchain.
- Name the root cause; symptom-only patches are not acceptable.
- Two human gates are non-negotiable: tests verified before PR, PR approved before merge.
- Every PR carries both artifacts: the committed CHANGELOG line and the posted agent trace.
