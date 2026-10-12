# Project registry — where this repo lives in the shared Jira, Confluence, and prod

Read by `/jira-task`, `/analyze-project`, `/docs-update`, and `/prod-check`.
**Template until filled in** — any skill that finds a `<...>` it needs asks for the value once, writes it here, and continues. Never guess a value.

The Jira project and Confluence space are **shared across several repos**, so every issue and page this repo creates must carry the identifiers below — that is the only thing that tells this project's work apart from the others.

## Jira
| key | value | notes |
|-----|-------|-------|
| Jira site | `grindlab.atlassian.net` | passed as `cloudId` |
| Jira project key | `KAN` | shared by several repos |
| Project label | `baraholka` | **added to every issue** — the primary filter. Lowercase, no spaces |
| Project component | `<none \| component name>` | set too, if the shared project models repos as components |
| Parent epic | `<none \| KAN-1>` | default parent for new issues, if your board uses one epic per repo |

### Board — Kanban
`KAN` is Jira's default **team-managed Kanban** project. Out of the box it has:
| | default | if your board differs |
|-|---------|-----------------------|
| Columns / statuses | `To Do` → `In Progress` → `Done`, plus **`Descope`** | list yours here, e.g. `To Do → In Progress → In Review → Done` |
| Issue types | `Epic`, `Task`, `Subtask` — `Bug`/`Story` only if added | list yours here |

Status rules every skill follows:
- Move only to a status that `getTransitionsForJiraIssue` actually offers. Never invent one.
- **`Descope`** is the human's "won't do" decision. **Claude never moves an issue into or out of `Descope`**, never implements a descoped issue, never comments on one, and never refiles its finding as a new issue — a descoped idea stays declined.
- **"In Review"** (PR open): use it if it exists; otherwise leave the issue in `In Progress` and comment the PR link.
- **"Blocked"**: Kanban has no such status by default. Leave the status as it is, add the label `blocked`, and comment the reason.
- **`Done`** only when the PR merges, never at PR time.

Project JQL — every skill scopes searches with this, never the bare project:
`project = KAN AND labels = baraholka`

## Confluence
| key | value | notes |
|-----|-------|-------|
| Space key | `<SPACE>` | shared by several repos |
| Project root page | `<page id or URL>` | everything `/docs-update` writes lives **under** this page |
| Title prefix | `<App Base>` | page titles are unique per space, so every managed page is `"<prefix> — <Title>"` |
| Description doc | `<page id or URL \| none>` | the human-owned project description — read, never overwritten |

## Production
| key | value | notes |
|-----|-------|-------|
| Prod URL | `<https://app.example.com>` | the only non-local origin `/prod-check` may browse |
| Extra allowed origins | `<none \| https://api.example.com>` | e.g. the API the frontend calls |
| Test account | `<none \| in .env.claude as PROD_TEST_USER / PROD_TEST_PASSWORD>` | a dedicated low-privilege account — never a real user's |
| Kube context / namespace | `<none \| prod-ctx / app>` | optional, for read-only `kubectl logs` during `/prod-check` |

### Critical journeys
What `/prod-check` walks every run, in priority order. Read-only steps only — mark anything that writes data `(writes — skip)`.
1. `<Landing page loads, nav links resolve>`
2. `<Log in with the test account → dashboard>`
3. `<...>`

### Do not touch
Pages, buttons, or flows `/prod-check` must never trigger, even read-only-looking ones.
- `<Checkout / payment>`
- `<Anything that sends email or notifications>`
