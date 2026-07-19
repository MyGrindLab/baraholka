#!/usr/bin/env bash
# PreToolUse guard for Bash calls. Reads the tool call JSON on stdin.
# Exit 2 blocks the command and feeds the message back to Claude.
set -euo pipefail

payload="$(cat)"
cmd="$(printf '%s' "$payload" | (command -v jq >/dev/null && jq -r '.tool_input.command // ""') || echo "")"

# Block obviously destructive / unsafe patterns. Extend as needed per project.
block() { echo "BLOCKED by claude-toolkit guard: $1" >&2; exit 2; }

case "$cmd" in
  *"rm -rf /"*|*"rm -rf /*"*|*":(){ :|:& };:"*) block "destructive filesystem/fork command" ;;
  *"git push --force"*|*"git push -f"*)          block "force-push — do this manually if you really mean it" ;;
  *"git push"*"main"*|*"git push"*"master"*)     block "direct push to main/master — open a PR instead" ;;
  *"DROP DATABASE"*|*"TRUNCATE"*)                block "destructive SQL — run manually with a backup" ;;
esac

exit 0
