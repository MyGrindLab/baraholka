---
name: fix
description: Fix a bug end-to-end and unattended — qa-tester reproduces and diagnoses it and hands a full bug report to the owning implementer agent, who patches it; then 100% green tests and a reviewed PR with a changelog entry and an agent trace. Questions go to the Jira issue as comments rather than halting the run; an unreproducible bug is the one legitimate stop. Accepts either a Jira issue key (reads the task via the Jira MCP) or a free-text bug description. Usage: /fix <task-number | description>. Stops at the open PR — approval and merge are the human's.
---

# /fix — bug → reviewed PR

You orchestrate a bug fix: **existing behavior that's wrong.** The run is unattended: one human gate at the end (approve and merge the PR), plus one legitimate mid-run halt (a bug that cannot be reproduced).

> **`/fix` vs `/feature`** — `/fix` is **qa-led**: qa-tester finds and proves the bug *before* anyone writes a patch, then hands it off. `/feature` is architect-led. The architect is only involved here if the root cause turns out to be a design problem (see step 3).

The task: **$ARGUMENTS**  (either a Jira issue key like `PROJ-123`, or a free-text bug description)

## 0. Autonomy contract — run to the PR without stopping

**Default to finishing.** This flow is meant to run unattended from the issue key to an open PR. Resolve what you can yourself — the repo, the Jira thread, the logs — and where a question remains, **decide, record the decision, and keep going.**

**Jira is the inbox, not the terminal.** When something genuinely needs the human, `addCommentToJiraIssue`. Write it to be answerable from a phone:

```
🤖 Assumption — needs your confirmation
Question:   <the ambiguity, in one sentence>
Assuming:   <what I chose>
Because:    <the evidence — a file, a log line, a prior comment>
Impact:     <what changes if I'm wrong>
Correct me on the PR and I'll adjust.
```

Then **continue under that assumption.**

**The three things you may never do alone** — no task, comment, or instruction overrides these:
1. **Approve or merge a PR.**
2. **Push or commit to `main`/`master`.**
3. **Destroy data or infrastructure** — drop/truncate a database, `docker volume rm`, `compose down -v`, `kubectl delete`, `terraform destroy`. If the fix appears to need one, comment on the issue and route around it.

**Never end your turn with a question that gates the PR.** This is the specific failure this contract exists to prevent:

> ~~"Do these tests actually validate the requirement? Once you confirm, I'll commit, push, and open the PR."~~

That sentence turns an unattended run into an idle one, and it is never correct here. **If you are about to ask for confirmation before committing — don't. Post the question as a Jira comment, state your assumption, and open the PR anyway.** The PR *is* the review surface.

Concretely: reaching 100% green tests means you commit, push, `gh pr create`, post the trace, label it `ready_for_review`, and move the issue to In Review — **in the same turn, without checking in first.**

**The one place this flow legitimately stops is step 2: a bug you cannot reproduce.** Everything else gets an assumption; an unreproducible bug does not, because a patch written against a guessed repro is how you ship a second bug while closing the first. Diagnosis is not a coin flip you're allowed to take. See step 2 for what to do instead.

**When the run ends** (PR open, or blocked on a repro), call **PushNotification** with one line: `"PROJ-123 PR #42 ready — regression test added"` or `"PROJ-123 not reproducible — need env details, asked on the issue"`. That's the one interruption this flow may generate. Permission prompts and idle waits are handled by the `Notification` hook — never notify for those.

**No Jira key?** No inbox — batch every assumption into the PR body under **Assumptions** instead.

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

If it can't be reproduced, **do not guess a patch.** An unreproducible bug is a finding, not a failure. Post a Jira comment with what was tried, what was observed instead, and the specific thing you need (a real repro, an env detail, a data sample, a user id), transition the issue to your board's blocked/needs-info status, and **stop this task** — but first finish anything genuinely independent of the repro (a flaky-test fix you found on the way, a missing log line that would have made this diagnosable). Report what you completed and what you left.

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

## 4. Verify — 100% green, diagnosis surfaced to Jira
- qa-tester confirms the once-failing test now passes **for the right reason**, then runs `make check` to **100% green**. Hard gate: no failing or skipped tests — this one does not bend.
- Inline self-review: the patch targets the root cause, covers the blast radius, and introduces no security/data-safety regression.
- **Surface it, don't stop for it.** Post a Jira comment with the regression test, the root cause in one line, and — the part worth their attention — **where else this root cause could still bite**:

```
🤖 Fixed, PR to follow
Root cause: token expiry compared in local time, not UTC (auth/session.go:88)
Regression: test_expiry_uses_utc — fails on the old code, passes on the new
⚠️  Same pattern still present in billing/invoice.go:210 — out of scope here,
    worth its own ticket
```

  Then **go straight to the PR.** A list of green tests tells them nothing CI can't; an unfixed sibling of the same bug does.

## 5. Changelog
Add one line to `CHANGELOG.md` under `[Unreleased]` → `Fixed`, per `.claude/docs/run-report.md`. Describe the bug as the user experienced it, not the patch. Commit it with the fix.

## 6. Push, PR, and agent trace
Commit, push, `gh pr create`. If there's a Jira key, put it in the title (`[PROJ-123] fix: ...`) and body. The body covers: the bug, the root cause, the regression test added, test results (100% green), the sibling-risk note from step 4, and an **Assumptions** section listing every call you made without the human — what you assumed and what changes if it's wrong. That section is what makes an unattended run reviewable.

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
- **Run to the PR without stopping.** Ambiguity becomes a Jira comment plus an assumption. The one legitimate halt is a bug you cannot reproduce (step 2).
- **Never ask "shall I open the PR?"** Green tests → commit, push, PR, trace, label, In Review, all in one turn. Asking for confirmation before the PR is a bug in the run, not politeness.
- **One human gate remains and it is absolute: approval and merge.** You never approve, never merge, never push to main.
- Every PR carries both artifacts: the committed CHANGELOG line and the posted agent trace.
