
#!/usr/bin/env bash
# Desktop notification. Two callers:
#
#   1. the Notification hook in settings.json — fires when Claude needs
#      permission or has been waiting on you for ~60s. Reads the event JSON
#      on stdin and pulls .message out of it.
#   2. a skill at a human gate — `notify.sh "tests ready for your review"`.
#      /feature and /fix call it when they stop and hand you something.
#
# Never fails the caller: every path exits 0. A missing notifier degrades to
# a terminal bell rather than breaking the hook.
set -uo pipefail

title="claude-code"
[ -n "${CLAUDE_PROJECT_DIR:-}" ] && title="claude-code · $(basename "$CLAUDE_PROJECT_DIR")"

if [ $# -gt 0 ]; then
  msg="$*"
else
  # hook mode: the event JSON arrives on stdin
  msg="$(cat 2>/dev/null || true)"
  if command -v jq >/dev/null 2>&1 && [ -n "$msg" ]; then
    msg="$(printf '%s' "$msg" | jq -r '.message // "needs your input"' 2>/dev/null || echo "needs your input")"
  else
    msg="needs your input"
  fi
fi
[ -z "$msg" ] && msg="needs your input"

case "$(uname -s)" in
  Darwin)
    # osascript takes an AppleScript string literal — escape \ and " or a
    # message containing a quote silently produces no notification at all.
    esc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
    osascript -e "display notification \"$(esc "$msg")\" with title \"$(esc "$title")\" sound name \"Glass\"" \
      >/dev/null 2>&1 || printf '\a'
    ;;
  Linux)
    if command -v notify-send >/dev/null 2>&1; then
      notify-send "$title" "$msg" >/dev/null 2>&1 || printf '\a'
    else
      printf '\a'
    fi
    ;;
  *) printf '\a' ;;
esac

exit 0
