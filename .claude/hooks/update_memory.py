#!/usr/bin/env python3
"""SessionEnd: update 0000-memory.md and 0000-user.md from today's session log."""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not repo or not repo.exists():
        return

    mem_dir = repo / ".memsearch" / "memory"
    daily_log = mem_dir / f"{date.today().isoformat()}.md"
    updatable = {
        "0000-memory.md": mem_dir / "0000-memory.md",
        "0000-user.md": mem_dir / "0000-user.md",
    }

    for path in [daily_log, *updatable.values()]:
        if not path.exists():
            return

    log_text = daily_log.read_text()
    if len(log_text.splitlines()) < 10:
        return  # Too little content to analyse

    current = "\n\n".join(
        f"=== CURRENT {name} ===\n{path.read_text()}"
        for name, path in updatable.items()
    )

    prompt = (
        "You are a memory curator for a software project. "
        "Review the session log and update the curated memory files only when "
        "concrete factual changes occurred — new architectural decisions, components "
        "added or removed, key metrics changed, dev commands changed, or new user "
        "communication preferences discovered. "
        "Ignore routine coding tasks, bug fixes, test runs, and informational questions.\n\n"
        f"=== TODAY'S SESSION LOG ===\n{log_text}\n\n"
        f"{current}\n\n"
        "If no updates are needed, output exactly: NO_UPDATES\n\n"
        "If updates are needed, output only the files that changed, in this format:\n"
        "FILE: <filename>\n"
        "<complete updated file content>\n"
        "---END---"
    )

    result = subprocess.run(
        [
            "claude", "-p",
            "--model", "haiku",
            "--no-session-persistence",
            "--strict-mcp-config",
            "--no-chrome",
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=90,
    )

    response = result.stdout.strip()
    if not response or "NO_UPDATES" in response:
        return

    for name, content in re.findall(
        r"FILE: (0000-\w+\.md)\n(.*?)---END---", response, re.DOTALL
    ):
        if name in updatable and updatable[name].exists():
            updatable[name].write_text(content.strip() + "\n")


if __name__ == "__main__":
    main()
