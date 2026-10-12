---
name: jira-task
description: Create one well-formed Jira issue in the shared Jira project — right type, summary, labels (project label always), component, priority, parent, and a templated description with acceptance criteria — after a duplicate check. Shows the draft and creates it on confirmation. Usage: /jira-task <what needs doing> [bug|story|task].
---

# /jira-task — a sentence → a ready-to-pick-up issue

You turn a loose request into one Jira issue that someone can start without asking a question. The Jira project is **shared with other repos**, so the project label is what makes the issue findable — an issue without it is effectively lost.

The request: **$ARGUMENTS**

## 1. Load the config
Read `.claude/docs/project.md` (site, project key, project label, component, parent epic) and `.claude/docs/jira-task-format.md` (fields, labels, templates). If a Jira value you need is still `<...>`, ask for it once, write it into `project.md`, and continue. Never guess a project key or label — a wrong one files the issue under another team's project.

## 2. Understand and enrich
- Decide the **type**: an explicit `bug|story|task` in the arguments wins; otherwise infer it (wrong behavior → Bug, new user-visible behavior → Story, anything else → Task) and say which you picked.
- **Ground it in the repo.** Find the code the issue touches (Grep/Glob, read the relevant files) so the description names real paths — `backend/api/user.go:88`, not "the user handler". For a Bug, look for the likely cause and put it under *Suspected cause*; label it a suspicion.
- Pick the **area** and **kind** labels and the **severity** per the format doc.
- Write acceptance criteria that are checkable. "Works correctly" is not a criterion; "Given an empty email, the form shows *Email is required* and sends no request" is.
- Don't invent facts the request doesn't support — repro steps you didn't verify, numbers you don't have. Put an unknown under *Notes* as an open question instead.

## 3. Check the project's schema
`getJiraProjectIssueTypesMetadata` → the real issue type names; `getJiraIssueTypeMetaWithFields` for the chosen type → which fields are required and whether `labels`, `components`, `priority`, `parent` are on the create screen. Drop a field the screen doesn't have (and say so) rather than letting the create fail. A required field you can't fill from the request → ask.

## 4. Duplicate check
Run the duplicate search from the format doc (always scoped by the project label). Duplicate → stop and offer to comment on the existing issue instead. Related → plan a "relates to" link.

## 5. Show the draft, then create
Show the draft exactly as it will be filed:

```
Type:      Bug          Priority: High          Parent: KAN-1
Labels:    app-base, claude-created, area-backend
Summary:   Login returns 500 on an empty email
Links:     relates to KAN-88
--- description ---
<full markdown>
```

Create on confirmation (`createJiraIssue`, description as markdown). If the user edits the draft, apply the edit and create — don't re-show it unless they ask. Then follow *After creating* in the format doc: re-read the issue, confirm labels and parent landed, add any planned links, report `KEY — summary — URL`.

## Rules
- One request → one issue. If the request is really three pieces of work, propose three drafts and let the user pick, rather than one issue with three unrelated ACs.
- Always the project label. Always scoped searches. Never a bare `project = KAN` query.
- Never transition, assign, or edit other issues — this skill creates; the only write to an existing issue is a comment or link from the duplicate check.
- No secrets, tokens, customer data, or full stack traces with personal data in the description — the project is shared.
