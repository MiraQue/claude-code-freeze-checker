"""
hook_stop.py - Stop hook

Writes status="waiting" to heartbeat file when Claude finishes responding.
This lets the Freeze Checker show "Sit" (teal) instead of THINK (blue).
"""

import json
import time
from pathlib import Path

HEARTBEAT_FILE = Path.home() / ".claude" / "freeze_checker_heartbeat.json"


def main():
    payload = {
        "status": "waiting",
        "timestamp": time.time(),
        "tool": "",
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception:
        pass


if __name__ == "__main__":
    main()
