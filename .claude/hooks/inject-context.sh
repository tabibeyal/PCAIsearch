#!/usr/bin/env bash
# SessionStart hook: inject full content of curated 0000-*.md context files.
# Runs alongside memsearch's hook, which injects recent daily logs separately.

exec < /dev/null

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

# Check memsearch plugin health — warn if fixes were overwritten by a plugin update
plugin_warnings=""
stop_hook=$(ls ~/.claude/plugins/cache/memsearch-plugins/memsearch/*/hooks/stop.sh 2>/dev/null | tail -1)
if [ -n "$stop_hook" ]; then
  if ! grep -q "CLAUDE_PLUGIN_ROOT:-" "$stop_hook" 2>/dev/null; then
    plugin_warnings="${plugin_warnings} PLUGIN UPDATE DETECTED: memsearch stop.sh fix was overwritten — daily session logs will stop writing. Run the fix-memsearch-session-start skill."
  fi
fi
session_start_hook=$(ls ~/.claude/plugins/cache/memsearch-plugins/memsearch/*/hooks/session-start.sh 2>/dev/null | tail -1)
if [ -n "$session_start_hook" ]; then
  if ! grep -q "Session-start ONNX indexing disabled" "$session_start_hook" 2>/dev/null; then
    plugin_warnings="${plugin_warnings} PLUGIN UPDATE DETECTED: memsearch session-start.sh ONNX fix was overwritten — system slowdowns may occur. Run the fix-memsearch-session-start skill."
  fi
fi

status="[context] ${count} curated file(s) loaded"
[ -n "$plugin_warnings" ] && status="${status} |${plugin_warnings}"
json_status=$(printf '%s' "$status" | _json_encode)
json_context=$(printf '%s' "$context" | _json_encode)

printf '{"systemMessage": %s, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": %s}}\n' \
  "$json_status" "$json_context"
