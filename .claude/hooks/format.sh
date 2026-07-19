#!/usr/bin/env bash
# PostToolUse formatter. Self-detects the toolchain and no-ops if it's absent,
# so it is safe to run in any repo. Reads the tool call JSON on stdin.
set -euo pipefail

payload="$(cat)"
file="$(printf '%s' "$payload" | (command -v jq >/dev/null && jq -r '.tool_input.file_path // ""') || echo "")"
[ -z "$file" ] && exit 0
[ -f "$file" ] || exit 0

case "$file" in
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.md)
    command -v npx >/dev/null && [ -f package.json ] && npx --no-install prettier --write "$file" 2>/dev/null || true ;;
  *.py)
    command -v ruff >/dev/null && ruff format "$file" 2>/dev/null || true ;;
  *.go)
    command -v gofmt >/dev/null && gofmt -w "$file" 2>/dev/null || true ;;
esac

exit 0
