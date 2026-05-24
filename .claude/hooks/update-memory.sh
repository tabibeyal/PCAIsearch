#!/usr/bin/env bash
# SessionEnd hook: update curated memory files from today's session log.
exec < /dev/null

REPO="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for p in "$HOME/.local/bin" "$HOME/.cargo/bin" "$HOME/bin" "/usr/local/bin"; do
  [[ -d "$p" ]] && [[ ":$PATH:" != *":$p:"* ]] && export PATH="$p:$PATH"
done

python3 "$SCRIPT_DIR/update_memory.py" "$REPO" 2>/dev/null

# Push updated memory files and today's daily log back to Google Drive
rclone sync "$REPO/.memsearch/memory" pcai-memory: --include "*.md" --quiet 2>/dev/null
exit 0
