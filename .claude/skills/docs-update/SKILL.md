---
name: docs-update
description: Sync this repo's documentation into the shared Confluence space — a managed page tree (overview, architecture, components, runbook, API, release notes) under the project's root page, generated from what the code actually is. Updates only pages it manages, never overwrites human-written pages, never deletes. Shows the plan before writing. Usage: /docs-update [page | topic] — empty syncs the whole tree.
---

# /docs-update — the repo → Confluence, kept honest

You keep this project's Confluence pages in step with the code. The Confluence space is **shared with other repos**, so everything you write lives under this project's root page, with this project's title prefix — and you never touch a page you don't manage.

Scope: **$ARGUMENTS** (empty → the full tree; a page name like `architecture` or a topic like `the new billing API` → just that).

## 1. Load the config
Read `.claude/docs/project.md` — space key, project root page, title prefix, description doc. If any is still `<...>`, ask once, write it into `project.md`, continue. Never pick a space or parent page on your own: a page created at the wrong place in a shared space is someone else's clutter.

## 2. The managed tree
Under the project root page:

| page title | source of truth in the repo |
|------------|-----------------------------|
| `<prefix> — Overview` | root `CLAUDE.md` + `README.md`: what it is, who it's for, layout table, links to Jira (project JQL) and the repo |
| `<prefix> — Architecture` | components, how they talk (compose services, ports, API boundaries), data stores; a mermaid/plain diagram if it helps |
| `<prefix> — Component: <name>` | one per **scaffolded** component: its `CLAUDE.md`, stack from its manifest, make targets, env vars by name (never values) |
| `<prefix> — Runbook` | `make help`, `make up`/`check`, deploy path (CI, k8s/Argo manifests), how to read logs, common failures |
| `<prefix> — API` | only if the repo has a spec (OpenAPI, proto, route table) — summarize it and link the file |
| `<prefix> — Release notes` | `CHANGELOG.md`, rendered by version |

Skip a page whose source doesn't exist yet (no API spec → no API page; empty `backend/` → no backend component page). Write *"Not yet built"* on the Overview instead of creating empty pages.

The **description doc** in `project.md` is human-owned. Read it for intent and link to it from Overview — never edit it.

## 3. Find what exists
`getConfluencePageDescendants` on the project root page; match pages by exact title. For each managed page, classify:
- **missing** → will create under the root page (component pages under Architecture, if it exists).
- **managed** → its body starts with the marker line from step 4 → will update.
- **human-owned** → same title, no marker → **don't overwrite.** Propose the change as a footer comment on that page (`createConfluenceFooterComment`) and report it.

Also search the space by title (`searchConfluenceUsingCql`, `space = SPACE AND title = "..."`) before creating — titles are unique per space, and the clash may be outside the root page.

## 4. Write the content
- **Distill, don't dump.** Pages explain and link; they don't paste files. Link to source in the repo (`<repo-url>/blob/<sha>/backend/api/user.go`) rather than copying code.
- **Only facts the repo confirms.** A command that isn't in the `Makefile`, a service that isn't in compose, a version that isn't in a manifest — leave it out. A `$(TODO)` target is documented as *not yet implemented*.
- **No secrets, ever** — env var names yes, values no; no internal hostnames or credentials from `.env*` files.
- Every managed page begins with this marker line, so the next run can recognize it:

  > 🤖 Maintained by `/docs-update` from `<repo>` @ `<short sha>` on `<YYYY-MM-DD>`. Edits here are overwritten on the next sync — propose changes as a comment or in the repo.

- For **updates**: `getConfluencePage` first (markdown) and compare. If the meaning hasn't changed, don't touch the page — no version bump just to change the date. If a human edited a managed page since the last sync (the content differs from what the marker's sha would produce, in ways that aren't from repo changes), keep their addition when it's still true and mention it in the report.

## 5. Show the plan, then write
Show a plan before any write:

```
create   App Base — Runbook                   (new: no runbook yet)
update   App Base — Architecture              (+ worker service, ports changed)
skip     App Base — Release notes             (no change since abc123)
comment  App Base — Overview                  (human-owned; proposed 2 corrections)
```

Write on confirmation: `createConfluencePage` / `updateConfluencePage` (markdown body, parent = root page). Report each page's title + URL.

## Rules
- Write only under the project root page, only with the title prefix, only to pages carrying the marker. Everything else gets a comment, not an edit.
- Never delete or move a page — even a managed one whose component was removed; mark it *"Component removed in <sha>"* and report it for the human to archive.
- The repo is the source of truth for facts; the description doc is the source of truth for intent. When they disagree, document the code and flag the gap.
- No secrets, no customer data, no pasted source files.
