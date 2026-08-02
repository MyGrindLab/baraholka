# Run report — what every `/feature` and `/fix` leaves behind

Two artifacts per run. Both are written before the PR is handed to the human.

## 1. CHANGELOG entry (committed)

One line in `CHANGELOG.md` under `[Unreleased]`, in the right bucket (`Added` / `Changed` / `Fixed`).

Write it for someone reading release notes — the user-visible change, not the patch:

- ✅ `Login no longer crashes on an empty email ([#13](url), PROJ-124)`
- ❌ `Add null check in validateEmail()`

One line per run. If a feature genuinely delivers two user-visible things, two lines. Never a paragraph — the detail lives in the trace below.

## 2. Agent trace (posted to the PR, not committed)

A reviewer should be able to read this and understand **how the change was produced** — who analyzed what, how the work was split, who touched which files and why — without re-deriving it from the diff.

Write it to the scratchpad and post it with `gh pr comment <pr> --body-file <path>`. Don't commit it: it describes one run, and committing agent traces turns the repo into a log.

**Hard cap: ~50 lines.** No diffs, no file contents, no passing-test output. If it's longer than the PR description, it's wrong.

```markdown
## 🤖 How this was built

**Task** — <one line: what was asked, and how it was interpreted if that wasn't obvious>

**Plan** (architect) — <2-4 lines: the approach chosen, the contract/boundary it hangs on,
and the one alternative rejected + why. For /fix, replace with **Diagnosis** (qa-tester):
symptom → reproduction → root cause in one sentence each.>

**Work split**

| agent | files | what & why |
|-------|-------|-----------|
| `backend-go` | `backend/api/health.go` | added the endpoint + wired the route |
| `frontend-react` | `frontend/src/…` | consumed it in the status widget |

**Verification** — <the make targets run, in containers, and their results:
`make check` → 42 passed, 0 failed. Note E2E separately if it ran.>

**Decisions** — <only the non-obvious ones a reviewer would otherwise have to ask about.
Omit the section entirely if there were none.>

**Open items** — <follow-ups, known gaps, anything deliberately left out. Omit if none.>
```

### Rules
- **Honest, not flattering.** Record what actually happened: a reproduction that failed, a task handed back and redone, an assumption made when the requirement was ambiguous. A trace that reads like everything went perfectly is a trace nobody will trust twice.
- Name real agents and real paths. "Various changes were made" is worse than no trace.
- One trace per PR. If you push follow-up commits after review, edit the existing comment rather than posting a second one.
