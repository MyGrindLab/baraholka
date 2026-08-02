---
name: init-project
description: Initialize a freshly forked repo — read the project description from a Confluence/Jira doc link or a Jira project key via the atlassian MCP, confirm the frontend/backend/infrastructure layout, then write a common root CLAUDE.md + README.md. Documentation only: it never scaffolds a component or picks a framework. Usage: /init-project <confluence-url | PROJ | description>. Run once, right after forking.
---

# /init-project — fork → a repo that describes itself

You turn this freshly forked template into *this* project's repo: `CLAUDE.md` and `README.md` stop describing "app-base" and start describing the real thing. Run once, right after forking. One human gate at the end (you show the changes, the user approves the commit).

This base is usually forked into a **monorepo**, so the defining job of this skill is the **split**: the root files stay common, per-package detail goes into nested files. Get that wrong and the root `CLAUDE.md` becomes a pile of half-true facts loaded on every message.

The project: **$ARGUMENTS** — a **link to the project description doc** (Confluence page, the best input), a Jira project key like `PROJ`, free text, or several of these together.

## 1. Resolve the input
`cloudId`: take the **hostname straight from the URL** (`acme.atlassian.net`) and pass it as `cloudId` — that works for every atlassian tool. Only fall back to `getAccessibleAtlassianResources` if it's rejected or there's no URL to read it from.

| Input | What to do |
|-------|-----------|
| `…/wiki/spaces/SPACE/pages/123456789/Title` | `getConfluencePage` with `pageId: "123456789"` → **step 2a** |
| `…/wiki/x/Fc1bBw` (tiny link) | `getConfluencePage` with `pageId: "Fc1bBw"` — it accepts tiny-link IDs → **step 2a** |
| `…/wiki/spaces/SPACE/overview` (or a space link) | `getPagesInConfluenceSpace` for that space key, pick the overview/home page → **step 2a** |
| `…/jira/software/projects/PROJ/…` or `…/browse/PROJ-123` | project key is `PROJ` → **step 2b** |
| A bare key like `PROJ` | → **step 2b** |
| A non-Atlassian URL (Notion, Google Doc, raw page) | `WebFetch` it; if it needs auth, ask the user to paste the text |
| Free text | that *is* the description → skip to step 3 |
| Nothing | list visible Jira projects (`getVisibleJiraProjects`) and ask which one, offering "none — I'll describe it myself" |

**Both a doc link and a key?** Use both — the doc for intent and architecture, Jira for the key, components, and issue history. If they disagree, the doc wins on *what we're building* and Jira wins on *how the board is organized*; say so when you summarize.

If a page 404s or the MCP isn't authenticated, say which it was — a private page and an unauthenticated server need different fixes (share the page vs. run `/mcp`). Then offer to continue from pasted text rather than stalling.

## 2a. Read the description doc
This is your primary source when given — a written project description beats anything inferred from issue titles.
- `getConfluencePage` with `contentFormat: "markdown"` for the body.
- If the page reads like an **index/overview** (mostly links, short body), pull one level of children with `getConfluencePageDescendants` (`depth: 1`) and read the ones that look load-bearing — architecture, components/services, stack, glossary, non-goals. Don't recurse the whole space.
- Follow in-page links to sibling pages **only** when they're clearly part of the description; skip meeting notes, retros, and status updates.

Extract: what the product does and for whom, scope and non-goals, the component/service breakdown (this often *is* the monorepo layout), the intended stack, and domain vocabulary worth putting in the docs. Keep the page URL — it goes in the README.

## 2b. Read the Jira project
Gather, in this order, stopping when you have enough:
- `getVisibleJiraProjects` with the key as `searchString` → **name, key, description, lead, project type**. Jira project descriptions are often one stale line — treat a doc from 2a as the better source when you have both.
- **Components** (`getJiraProjectIssueTypesMetadata`, and the `components` field on issues) → in a monorepo these usually mirror the packages one-for-one. Note the mapping; you'll use it in step 4.
- Recent/oldest issues (`searchJiraIssuesUsingJql`, e.g. `project = PROJ ORDER BY created ASC`, ~20-30 issues) → what the project actually builds: domain nouns, named services, recurring stack mentions. Epics and the earliest issues are the most informative.
- **No doc link was given?** Go find one: `search` or `searchConfluenceUsingCql` for the project name / "overview" / "architecture", plus `getJiraIssueRemoteIssueLinks` on an epic (project docs are frequently linked there). If you find a likely page, read it as in 2a and tell the user which page you used — they may want to pass a better one.

Summarize back to the user in ~5 lines what you learned, and **name your sources** (doc page title + URL, Jira key), before you write anything. Read-only — **never** create, edit, comment on, or transition a Jira issue, and never edit a Confluence page, in this skill.

## 3. Map the repo
Jira says what the project is *for*; the repo says what it *is*. The repo wins on anything factual.

**The layout is fixed by this template** — `frontend/` (required), `backend/`, `infrastructure/`, root `Makefile`, `CHANGELOG.md`. Confirm it rather than discovering it. If the fork has grown extra top-level components (`worker/`, `mobile/`), add them as rows; don't invent a different structure.

**Expect the components to be empty.** A fresh fork ships the directories and the `Makefile` target names as the agreed structure — no framework, no compose file, no Dockerfiles. That is the normal starting state, not a problem to fix: record the structure, note that scaffolding is pending, and move on. Do **not** scaffold a component, pick a framework, or write `infrastructure/docker-compose.yml` yourself — that's `devops` work, and the framework choice is the user's.

For each component that *does* have code, record from **its own** manifest — `frontend/package.json`, `backend/go.mod` or `backend/pyproject.toml`:

| path | what it is | language/framework | test | lint | Jira component |
|------|-----------|--------------------|------|------|----------------|

Then reconcile with the **containers**: `infrastructure/docker-compose.yml` services, their Dockerfiles, ports and env vars, and the `Makefile` variables (`FRONTEND_TEST`, `BACKEND_TEST`, …). The per-component commands you record must be the ones the Makefile actually runs *inside the container* — a command that only works on a host is the wrong answer here even if it's in the manifest.

**Never invent a command.** If `pytest`/`vitest`/`go test` isn't visible in the component's manifest, leave the `<...>` placeholder in both the `Makefile` and the docs, and list it in the open questions rather than writing a command that doesn't run. On a fresh fork this means *every* command placeholder stays as-is — that's the correct outcome.

## 4. Write the files — the split
### Root `CLAUDE.md` — only what is true for *every* package
The test: **if a fact is false for any component in the repo, it does not belong in the root file.** A backend test command is not a root fact when `frontend/` doesn't use it.

Keep the existing skeleton and put here, and only here:
- The real project name, and a **one-or-two-sentence** "what this does" distilled from the description doc. Distilled — never paste the page in. A multi-page Confluence description compresses to two sentences here and a link in the README.
- `Jira project: PROJ` — so `/feature` and `/fix` know where issue keys come from.
- **Repo layout** — the component table from step 3, kept to `path → what lives there → owner agent`. This is the highest-value thing in the root file: it's how work gets routed to the right directory.
- **Repo-wide conventions only**: the Docker-only rule, the `Makefile` entry points (`make help` / `up` / `check`), `devops` ownership of `infrastructure/` + `Makefile`, the changelog + agent-trace requirement, branch/PR rules.
- The existing pointers to agents, skills, and MCP servers.
- Drop the `# <PROJECT_NAME>` heading's "Base full-stack repo…" instruction block, and delete stack lines that don't apply.

**The root CLAUDE.md loads on every message — it must stay small.** Target under ~40 lines; the layout table earns its space, prose does not.

### Nested `CLAUDE.md` per component — only once there's code
`frontend/CLAUDE.md` and `backend/CLAUDE.md` load only when Claude reads files in that subtree, so detail there is nearly free — but **write one only when the component actually has a stack to describe**: its framework, its **make targets** (`make test-frontend`, not `npm test`), local conventions, gotchas, owning agent. Short (~15-25 lines), no restating of root facts.

On a fresh fork, skip these entirely. An empty directory needs no `CLAUDE.md`, and a file full of `<...>` is worse than none — it reads as fact once someone forgets it was a placeholder. Note the gap in the open questions instead.

### Leave the templates as templates
The `Makefile` ships as a skeleton (declared targets, `$(TODO)` bodies, commented-out variables) and `CHANGELOG.md` as an empty format. **Fill in only what a real manifest confirms**, and on a fresh fork that is usually nothing at all — which is the correct outcome, not a gap you should close.

Do not fill a placeholder with something plausible, and do not create `infrastructure/` compose files, Dockerfiles, or any component scaffold — those are `devops`-owned and depend on framework choices that aren't yours to make. A placeholder gets fixed; a wrong default gets trusted. List all of it as pending work in your report.

If the user later wants per-component workflow commands too, mention that skills can be directory-scoped the same way (a `.claude/skills/` under a component dir) — suggest it, don't build it now.

## 5. Rewrite README.md
Root README is for humans, so it can be longer — but same discipline: **orientation, not per-package docs.**
- What the project is and who it's for (from the description doc), the top-level architecture, the component table, and the bootstrap path from a clean clone — which is always **`make up`** here, since Docker is the only supported way to run this. Say that explicitly: no host toolchain needed.
- Keep the template README parts that stay true after forking: the `/feature` · `/fix` workflow, the subagent list, MCP servers, hooks, the GitHub Action, the two-human-gate autonomy contract. Trim the "how to fork the template" setup steps to a short "first-time setup" note — they've already been done.
- **Link the description doc** and the Jira project near the top, so the canonical source stays one click away and the README doesn't have to duplicate it.
- Per-component `README.md` only where one has a genuinely different run story. Don't generate stubs.

## 6. Prune the template
Ask before deleting, then apply:
- Remove the backend agent for the language `backend/` doesn't use (`backend-go` or `backend-python`) and its README/CLAUDE.md mentions. Check every component first — a repo with an extra Go worker alongside a Python API keeps both.
- Flag any other agent that clearly doesn't fit (e.g. `devops` when there's no infrastructure) — suggest, don't delete unprompted.
- Leave `.claude/skills/`, hooks, and `.mcp.json` alone.

## 7. Show, confirm, commit
- Show the full diff of the root `CLAUDE.md`, `README.md`, and `Makefile`, the full text of any nested `CLAUDE.md` you wrote, and list every deleted file.
- List **open questions** — every `<...>` you couldn't fill, every unverified command, every component not yet scaffolded, and everything you're handing to `devops` — as a short checklist. On a fresh fork this list is long by design; say so plainly rather than filling it in with guesses.
- If you touched the `Makefile`, check it still parses (`make help`). Don't build images.
- Ask for confirmation, then commit on a branch (`chore/init-project`) with a message naming the Jira project. **Don't push and don't open a PR** unless the user asks — this is usually the fork's first commit and it's theirs to place.

## Rules
- Read-only on Jira/Confluence. This skill never writes to the board or edits a page.
- The repo outranks the docs on facts (what the code *is*); the docs outrank the repo on intent (what it's *for*). Between sources: description doc > Jira project description > issue titles.
- Docs get **distilled and linked**, never copied. If you're tempted to paste a Confluence section, that's a sign it belongs behind the link.
- **Root files stay common.** A fact that's false for any component belongs in that component's nested `CLAUDE.md`, not the root. When in doubt, push it down.
- Root CLAUDE.md under ~40 lines, nested ones ~15-25. Detail for humans goes to README.md.
- The layout (`frontend/` · `backend/` · `infrastructure/` · root `Makefile`) is fixed by the template — confirm it, don't redesign it. Commands you record must be the containerized ones.
- **This skill writes documentation, not code.** It never scaffolds a component, chooses a framework, or authors compose/Dockerfiles — those are `devops` and user decisions. Empty components are the expected starting state; report them, don't fill them.
- Unknown stays unknown: a `<...>` placeholder plus an open question beats a plausible invention. Fabricated test commands are the main failure mode here.
- Run once per fork. If the root `CLAUDE.md` no longer has `<PROJECT_NAME>` in it, say the repo looks already initialized and ask whether to refresh it before overwriting.
