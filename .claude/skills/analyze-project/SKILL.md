---
name: analyze-project
description: Audit the repo for bugs, security issues, performance problems, tech debt, test gaps, and infra/DX gaps; verify every finding against the code, de-duplicate against open Jira issues, then file the approved ones in the shared Jira project with the standard format. Read-only on the code. Usage: /analyze-project [area | focus] — e.g. /analyze-project backend, /analyze-project security.
---

# /analyze-project — the repo → a prioritized, evidence-backed backlog

You review the codebase and turn what you find into Jira issues worth picking up. The value is in **precision, not volume**: ten verified findings with file:line evidence beat fifty plausible ones. A backlog full of noise teaches people to ignore issues labeled `claude-created`.

Scope: **$ARGUMENTS** (empty → the whole repo; a directory like `backend` → that component; a theme like `security` → that category across the repo).

## 0. Ground rules
- **Read-only on the code.** No edits, no commits, no branches. Running the containerized gates (`make check`, `make lint`) to collect real failures is fine; installing or running anything on the host is not.
- **Every finding needs evidence** — a file:line, a failing command's output, or a concrete input that breaks it. "This might be slow" with no evidence is not a finding.
- **Nothing is filed until the user approves the list** (step 5). Creating thirty issues in a shared project is not reversible in any useful way.

## 1. Load the config and map the repo
Read `.claude/docs/project.md` and `.claude/docs/jira-task-format.md`; fill any `<...>` Jira value you need by asking once. Then map the repo: the components in `CLAUDE.md`'s layout table, each component's `CLAUDE.md`, manifests, `infrastructure/`, `Makefile`, CI config. If a component is still empty (fresh fork), say so and skip it — an empty directory is the expected state, not a finding.

## 2. Collect signals
Cheap, factual signals first:
- `make check` / `make lint` / `make test` — real failures and warnings, verbatim. (A `$(TODO)` target that isn't filled in yet is one *infra* finding, not one per target.)
- `TODO` / `FIXME` / `HACK` / `XXX` comments — read the code around each; only the ones describing a real defect or risk become findings.
- Dependency manifests — pinned versions with known problems, unused dependencies, missing lockfiles.

## 3. Review, by category
For a small repo, do this inline. For a large one, fan out **one agent per component** — its owner agent from the layout table (`frontend-react`, `backend-go`/`backend-python`, `devops`) — with a **read-only** brief: the categories below, the evidence rule, and "return findings, edit nothing". Verify what comes back yourself in step 4.

| category | look for |
|----------|----------|
| **bug** | logic errors, unhandled errors/nil/undefined, race conditions, off-by-one, wrong status codes, broken error paths, timezone/encoding mistakes |
| **security** | injection (SQL/command/template), missing authz checks, secrets in code or config, unsafe deserialization, permissive CORS, missing input validation at trust boundaries, vulnerable deps |
| **performance** | N+1 queries, unbounded queries/lists, missing indexes for real query patterns, work in hot loops, missing pagination, oversized frontend bundles |
| **test-gap** | core paths with no tests, tests that assert nothing, skipped/flaky tests |
| **tech-debt** | duplication worth removing, dead code, layering violations, misleading names — only where it costs something concrete |
| **infra / DX** | missing `Makefile` targets, things that only work on the host, missing healthchecks, CI that doesn't run `make check`, no resource limits in k8s manifests |
| **docs** | `CLAUDE.md`/README claims that are false about the code |

Skip style nits a linter would catch and taste-level preferences. They aren't issues.

## 4. Verify and de-duplicate
For **each** candidate, before it goes on the list:
- Re-open the cited code and confirm the problem is real in context — callers may already validate, a framework may already escape. Drop it if it doesn't hold up.
- Assign severity (format doc) and a **confidence**: `confirmed` (you traced it or a command proved it) or `likely` (strong evidence, not executed). No "possible" tier — those get dropped.
- Merge findings with the same root cause into one issue listing every site.
- Duplicate-search Jira per the format doc (scoped by the project label). Already tracked → mark `tracked: KAN-123` and don't refile; matches a **descoped** issue → mark `descoped: KAN-123`, don't refile and don't comment (the human declined it); add a comment only if you have meaningfully new evidence.

## 5. Report and get approval
Show a table, sorted by severity then confidence:

```
#  sev       conf       type  area      summary                                    evidence
1  critical  confirmed  Bug   backend   SQL injection in user search               backend/api/search.go:41
2  high      likely     Task  infra     CI never runs make check                   .github/workflows/ci.yml
3  medium    confirmed  Bug   frontend  Form submits twice on double-click         frontend/src/Login.tsx:58
-  medium    —          —     backend   Missing pagination on /orders              tracked: KAN-211
-  low       —          —     frontend  Migrate to CSS modules                     descoped: KAN-140
```

Then ask which to file — default offer: **all confirmed + likely at medium or above**, capped at ~15 per run. Lows go in the report only, unless the user asks for them.

**Security findings:** describe the class of problem and the location; don't paste a working exploit into a shared Jira project.

## 6. File them
For each approved finding, create the issue per the format doc: type, summary, labels (project label, `claude-created`, area, kind, **`from-analyzer`**, plus `analysis-<YYYY-MM-DD>` so one run's issues can be pulled up together), component, priority, parent, templated description with the evidence and suggested direction. Link findings that depend on each other ("blocks").

Finish with the list of created keys + URLs, the JQL that shows this run (`labels = analysis-<date>`), and what you dropped or skipped and why.

## Rules
- Precision over volume. If you're unsure a finding is real, it isn't on the list.
- Read-only on the repo. This skill files issues; `/feature` and `/fix` do the work.
- Always the project label and scoped searches — the Jira project is shared.
- Never transition, assign, close, or edit existing issues; the only write to them is a comment with new evidence.
