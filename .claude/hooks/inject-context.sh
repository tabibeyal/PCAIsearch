#!/usr/bin/env bash
# SessionStart hook: inject full content of curated 0000-*.md context files.
# Runs alongside memsearch's hook, which injects recent daily logs separately.

exec < /dev/null

# Pull latest curated files from Google Drive (non-blocking; failures are silent)
rclone copy pcai-memory: "$(git rev-parse --show-toplevel 2>/dev/null)/.memsearch/memory" \
  --include "0000-*.md" --quiet 2>/dev/null &

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
if [ -n "$GIT_ROOT" ]; then
  MEMORY_DIR="$GIT_ROOT/.memsearch/memory"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  MEMORY_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")/.memsearch/memory"
fi

_json_encode() {
  python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '""'
}

if [ ! -d "$MEMORY_DIR" ]; then
  echo '{}'
  exit 0
fi

context=""
count=0
for f in "$MEMORY_DIR"/0000-*.md; do
  [ -f "$f" ] || continue
  file_content="$(cat "$f")"
  [ -z "$file_content" ] && continue
  context="${context}${file_content}

---

"
  count=$((count + 1))
done

if [ "$count" -eq 0 ]; then
  echo '{}'
  exit 0
fi

status="[context] ${count} curated file(s) loaded"
json_status=$(printf '%s' "$status" | _json_encode)
json_context=$(printf '%s' "$context" | _json_encode)

printf '{"systemMessage": %s, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": %s}}\n' \
  "$json_status" "$json_context"
