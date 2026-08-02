
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

  # ONLY notify when Claude is actually blocked on the human. The Notification
  # event also fires for things that are merely informational — those must stay
  # silent, or the banner becomes noise and gets ignored exactly when it matters.
  case "$(printf '%s' "$msg" | tr '[:upper:]' '[:lower:]')" in
    *permission*|*"waiting for your input"*|*"needs your input"*|*approve*|*confirm*) ;;
    *) exit 0 ;;
  esac
fi
[ -z "$msg" ] && msg="needs your input"

# Testing this script should never pop a real banner. NOTIFY_DRY_RUN=1 prints
# the decision and sends nothing.
if [ -n "${NOTIFY_DRY_RUN:-}" ]; then
  printf 'would notify: %s — %s\n' "$title" "$msg"
  exit 0
fi

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

# --- Telegram ----------------------------------------------------------------
# Opt-in: skipped entirely when the vars are unset, so this stays safe to commit.
# Config comes from the repo-root .env (see .env.example) — copy it to .env and
# fill it in. .env is gitignored; never put the token in settings.json.
#
#   token:   message @BotFather -> /newbot
#   chat id: message your bot once, then read
#            https://api.telegram.org/bot<TOKEN>/getUpdates
#
# Runs in the background behind a hard 5s timeout, so a dead network delays the
# hook by seconds instead of hanging it.

if [ -f "${CLAUDE_PROJECT_DIR:-.}/.env" ]; then
  # shellcheck disable=SC1090
  set -a; . "${CLAUDE_PROJECT_DIR:-.}/.env" 2>/dev/null || true; set +a
fi

# Failing silently is right for a hook and wrong for setup: a typo'd token
# looks exactly like "not configured". NOTIFY_DEBUG=1 surfaces the API reply.
#   NOTIFY_DEBUG=1 .claude/hooks/notify.sh test
out=/dev/null; err=(); [ -n "${NOTIFY_DEBUG:-}" ] && { out=/dev/stderr; err=(-S); }

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  curl -s ${err[@]+"${err[@]}"} -m 5 -o "$out" \
    -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${title}: ${msg}" 2>>"$out" &
  wait 2>/dev/null || true
fi

exit 0
