#!/usr/bin/env bash
# PreToolUse guard for Bash calls. Reads the tool call JSON on stdin.
# Exit 2 blocks the command and feeds the message back to Claude.
#
# Two kinds of rule live here:
#   1. universally destructive things (rm -rf /, DROP DATABASE, terraform destroy)
#   2. this repo's own conventions from CLAUDE.md — Docker-only, PR-only,
#      merge/approve is human-only. A convention nobody enforces is a suggestion.
# Extend as needed per project; keep every message actionable.
set -euo pipefail

payload="$(cat)"
if ! command -v jq >/dev/null 2>&1; then
  echo "claude-toolkit guard: jq not found — command guard is INACTIVE (brew install jq)" >&2
  exit 0
fi
cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // ""')"
cmd_lc="$(printf '%s' "$cmd" | tr '[:upper:]' '[:lower:]')"

block() { echo "BLOCKED by claude-toolkit guard: $1" >&2; exit 2; }
deny()    { if [[ "$cmd"    =~ $1 ]]; then block "$2"; fi; }   # case-sensitive
deny_lc() { if [[ "$cmd_lc" =~ $1 ]]; then block "$2"; fi; }   # case-insensitive (SQL)

# --- destructive filesystem / shell -----------------------------------------
deny 'rm[[:space:]]+-[a-zA-Z]*[rf][a-zA-Z]*[[:space:]]+(/|~|\*|\$HOME)' \
     "recursive delete of an absolute/home/glob path — narrow the path or do it manually"
deny ':\(\)[[:space:]]*\{.*\|:&' "fork bomb"
deny 'chmod[[:space:]]+(-R[[:space:]]+)?777' "world-writable chmod — fix ownership instead"
deny '(^|[[:space:];&|])sudo[[:space:]]' "sudo — the agent never needs root; ask the human"
deny '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba)?sh' \
     "piping a remote script into a shell — vendor it or add a make target"
deny '>[[:space:]]*/dev/(sd|nvme|disk)' "writing to a raw device"

# --- git: work you cannot get back ------------------------------------------
deny 'git[[:space:]]+reset[[:space:]]+--hard'            "git reset --hard discards uncommitted work — stash first"
deny 'git[[:space:]]+clean[[:space:]]+-[a-zA-Z]*[fd]'    "git clean discards untracked files — list them first"
deny 'git[[:space:]]+(checkout|restore)[[:space:]]+(--[[:space:]]+)?\.([[:space:]]|$)' \
     "discards all working-tree changes — stash instead"
deny 'git[[:space:]]+push[[:space:]].*(--force([[:space:]]|$)|--force-with-lease|-f([[:space:]]|$))' \
     "force-push — do this manually if you really mean it"
deny 'git[[:space:]]+branch[[:space:]]+-D'               "force branch delete — human-only"
deny 'git[[:space:]]+(filter-branch|filter-repo)|git[[:space:]]+reflog[[:space:]]+expire|git[[:space:]]+gc[[:space:]]+.*--prune' \
     "history surgery — human-only"

# --- the PR flow is the contract (CLAUDE.md: never commit directly to main) --
deny 'git[[:space:]]+push([[:space:]]+-[^[:space:]]+)*([[:space:]]+[^[:space:]]+)?[[:space:]]+(main|master)([[:space:]]|$)' \
     "direct push to main/master — open a PR instead"
deny 'git[[:space:]]+push.*:(main|master)([[:space:]]|$)' \
     "direct push to main/master — open a PR instead"

branch="$(git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
case "$branch" in
  main|master)
    deny 'git[[:space:]]+commit' "commit on $branch — create feat/… or fix/… first"
    # only a *bare* push (no explicit branch) — `git push origin feat/x` from here is fine
    deny 'git[[:space:]]+push([[:space:]]+(--?[a-zA-Z-]+|origin|upstream|HEAD))*[[:space:]]*($|[;&|])' \
         "push from $branch — branch first, then open a PR"
    ;;
esac

# --- human-only gates (/feature and /fix both stop at the open PR) -----------
deny 'gh[[:space:]]+pr[[:space:]]+merge'                      "merging is the human's call — the skill stops at the open PR"
deny 'gh[[:space:]]+pr[[:space:]]+review.*--approve'          "self-approving a PR — the human reviews"
deny 'gh[[:space:]]+(repo[[:space:]]+delete|release[[:space:]]+delete)' "destroys a repo/release — human-only"

# --- data ---------------------------------------------------------------------
deny_lc 'drop[[:space:]]+(database|schema|table)'  "destructive SQL — run manually with a backup"
deny_lc 'truncate[[:space:]]'                      "destructive SQL — run manually with a backup"
if [[ "$cmd_lc" =~ delete[[:space:]]+from ]] && [[ ! "$cmd_lc" =~ where ]]; then
  block "DELETE without a WHERE clause"
fi
deny_lc 'alembic[[:space:]]+downgrade|migrate[[:space:]]+down' "migration rollback — run manually against a backup"

# --- containers & infra (devops-owned; volumes hold the dev data) ------------
deny 'docker[[:space:]]+system[[:space:]]+prune'                    "nukes shared docker state — do it manually"
deny 'docker[[:space:]]+volume[[:space:]]+(rm|prune)'               "deletes volume data — do it manually"
deny 'docker([[:space:]]+|-)compose.*down.*(-v([[:space:]]|$)|--volumes)' "down -v wipes the dev database — use make down"
deny 'kubectl[[:space:]]+delete'                                    "cluster deletion — devops does this manually"
deny 'terraform[[:space:]]+(destroy|apply.*-auto-approve)'          "unattended infra change — human-only"
deny 'helm[[:space:]]+(delete|uninstall)|argocd[[:space:]]+app[[:space:]]+delete' "tears down a release — human-only"

# --- Docker-only convention: builds/tests/installs go through the Makefile ---
deny '(^|[[:space:];&|])(npm|pnpm|yarn)[[:space:]]+(install|ci|run|test|build)([[:space:]]|$)' \
     "host toolchain — nothing runs on the host; use a make target (ask devops to add one)"
deny '(^|[[:space:];&|])(pip3?|poetry)[[:space:]]+(install|add|sync)([[:space:]]|$)' \
     "host toolchain — nothing runs on the host; use a make target (ask devops to add one)"
deny '(^|[[:space:];&|])(pytest|go[[:space:]]+(test|build|run|mod))([[:space:]]|$)' \
     "host toolchain — tests run in containers; use make test (ask devops to add the target)"

# --- secrets -------------------------------------------------------------------
deny 'git[[:space:]]+add[[:space:]].*\.env([[:space:]]|$)' "never commit .env — add it to .gitignore"
deny 'gh[[:space:]]+secret[[:space:]]+set'                 "writing a repo secret — the human does this"

exit 0
