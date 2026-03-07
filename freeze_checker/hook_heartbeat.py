"""
hook_heartbeat.py - PostToolUse hook

Writes status="active" to heartbeat file on every tool execution.
Claude Code calls this automatically via hooks in settings.json.
"""

import json
import os
import sys
import time
from pathlib import Path

HEARTBEAT_FILE = Path.home() / ".claude" / "freeze_checker_heartbeat.json"


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    if not tool_name:
        try:
            import select
            if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                raw = sys.stdin.read()
                if raw.strip():
                    data = json.loads(raw)
                    tool_name = data.get("tool_name", data.get("tool", ""))
        except Exception:
            pass
    if not tool_name:
        tool_name = "tool"

    payload = {
        "status": "active",
        "timestamp": time.time(),
        "tool": tool_name,
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception as e:
        print(f"[hook_heartbeat] write error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
