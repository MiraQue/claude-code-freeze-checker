"""
setup.py - PATLAS Tools Automated Setup

Installs dependencies and configures Claude Code hooks automatically.
Supports Windows and macOS.

Usage:
    python setup.py
"""

import sys
import os
import json
import subprocess
import platform
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.resolve()
CLAUDE_DIR   = Path.home() / ".claude"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def log(msg, color=RESET):
    print(f"{color}{msg}{RESET}")

def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*50}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*50}{RESET}")


# ------------------------------------------------------------------ #
#  Step 1: 環境チェック
# ------------------------------------------------------------------ #

def check_environment():
    header("Checking environment / 環境チェック")

    # Python version
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 9):
        log(f"Python 3.9+ is required. Found: {v.major}.{v.minor}", RED)
        sys.exit(1)
    log(f"  Python {v.major}.{v.minor}.{v.micro} ... OK", GREEN)

    # OS
    os_name = platform.system()
    log(f"  OS: {os_name} ... OK", GREEN)

    if os_name == "Darwin":
        log("  macOS detected. If tkinter is missing, run:", YELLOW)
        log("    brew install python-tk", YELLOW)

    return os_name


# ------------------------------------------------------------------ #
#  Step 2: pip パッケージのインストール
# ------------------------------------------------------------------ #

def install_packages():
    header("Installing packages / パッケージインストール")

    req_file = REPO_ROOT / "requirements.txt"
    log(f"  Running: pip install -r {req_file.name}")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(req_file),
            "--quiet"
        ])
        log("  All packages installed successfully.", GREEN)
    except subprocess.CalledProcessError as e:
        log(f"  pip install failed: {e}", RED)
        log("  Please run manually: pip install -r requirements.txt", YELLOW)


# ------------------------------------------------------------------ #
#  Step 3: settings.json にフックを設定
# ------------------------------------------------------------------ #

def update_claude_settings():
    header("Configuring Claude Code hooks / フック設定")

    hb_script   = REPO_ROOT / "freeze_checker" / "hook_heartbeat.py"
    stop_script = REPO_ROOT / "freeze_checker" / "hook_stop.py"

    # 既存の settings.json を読み込む
    settings = {}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            log(f"  Found existing settings.json", GREEN)
        except Exception:
            log("  Could not parse existing settings.json, creating new.", YELLOW)

    # フックを設定（既存フックを上書きしないよう配慮）
    existing_hooks = settings.get("hooks", {})

    new_hooks = {
        "PostToolUse": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": f'python "{hb_script}"'
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f'python "{stop_script}"'
                    }
                ]
            }
        ]
    }

    # マージ（既存フックを保持しつつ patlas-tools のフックを追加）
    for event, handlers in new_hooks.items():
        if event not in existing_hooks:
            existing_hooks[event] = handlers
        else:
            # 既に patlas-tools のフックが入っていなければ追加
            existing_cmds = [
                h.get("command", "")
                for group in existing_hooks[event]
                for h in group.get("hooks", [])
            ]
            if str(hb_script) not in " ".join(existing_cmds):
                existing_hooks[event].extend(handlers)
                log(f"  Added hook: {event}", GREEN)
            else:
                log(f"  Hook already exists: {event} (skipped)", YELLOW)

    settings["hooks"] = existing_hooks

    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    log("  settings.json updated successfully.", GREEN)


# ------------------------------------------------------------------ #
#  Step 4: Skills のインストール
# ------------------------------------------------------------------ #

def install_skills():
    header("Installing Claude Code skills / スキルインストール")

    skills_dir = CLAUDE_DIR / "skills"

    skill_defs = [
        {
            "name": "freeze-checker",
            "script": REPO_ROOT / "freeze_checker" / "freeze_checker.py",
            "triggers_en": ["start freeze checker", "launch freeze checker", "/freeze-checker"],
            "triggers_ja": ["フリーズチェッカーを起動", "フリーズチェッカー起動"],
            "message": "Freeze Checker started. A monitoring window appears on screen."
        },
        {
            "name": "image-viewer",
            "script": REPO_ROOT / "image_viewer" / "image_viewer.py",
            "triggers_en": ["start image viewer", "open image viewer", "/image-viewer"],
            "triggers_ja": ["画像ビューワーを起動", "画像ビューワー起動"],
            "message": "Image Viewer started. Drop an image file to display it."
        },
        {
            "name": "sprite-viewer",
            "script": REPO_ROOT / "image_viewer" / "sprite_viewer.py",
            "triggers_en": ["start sprite viewer", "open sprite viewer", "/sprite-viewer"],
            "triggers_ja": ["スプライトビューワーを起動", "スプライトビューワー起動"],
            "message": "Sprite Viewer started. Drop a sprite sheet to animate it."
        },
    ]

    for skill in skill_defs:
        skill_dir = skills_dir / skill["name"]
        skill_dir.mkdir(parents=True, exist_ok=True)

        triggers = "\n".join(
            [f'- "{t}"' for t in skill["triggers_en"] + skill["triggers_ja"]]
        )
        content = f"""# {skill["name"]}

## Trigger phrases
{triggers}

## What to do

Run the following Bash command in the background:

```bash
python "{skill["script"]}"
```

Use `run_in_background: true`.

After running, tell the user:
\"{skill["message"]}\"
"""
        with open(skill_dir / "SKILL.md", "w", encoding="utf-8") as f:
            f.write(content)

        log(f"  Skill installed: {skill['name']}", GREEN)

    # freeze-sprite skill（画像番号付き）
    sprite_skill_dir = skills_dir / "freeze-sprite"
    sprite_skill_dir.mkdir(parents=True, exist_ok=True)
    sprite_script = REPO_ROOT / "freeze_checker" / "freeze_sprite.py"
    sprites_dir   = REPO_ROOT / "freeze_checker" / "sprites"

    with open(sprite_skill_dir / "SKILL.md", "w", encoding="utf-8") as f:
        f.write(f"""# freeze-sprite

## Trigger phrases
- "start sprite freeze checker"
- "launch freeze sprite"
- "スプライトチェッカーアニメーションを起動"
- "スプライトチェッカーアニメーション起動"
- "スプライトチェッカーアニメーション[number]を起動"
- "/freeze-sprite"

## What to do

### Step 1: List available sprites
```bash
ls "{sprites_dir}"
```

### Step 2: Decide how to launch

**Pattern A: User specified a number** (e.g. "sprite checker animation 2")
→ Launch with that number:
```bash
python "{sprite_script}" 2
```

**Pattern B: No number, only 1 sprite** → Launch without argument.

**Pattern C: No number, multiple sprites**
→ Show list and ask: "Which sprite would you like to use? Please reply with a number."
Then launch with the chosen number.

**Pattern D: No sprites found**
→ Tell the user to add a 4x4 PNG sprite sheet to: `{sprites_dir}`

All commands use `run_in_background: true`.
""")
    log(f"  Skill installed: freeze-sprite", GREEN)


# ------------------------------------------------------------------ #
#  Step 5: sprites フォルダの確認
# ------------------------------------------------------------------ #

def check_sprites_folder():
    sprites_dir = REPO_ROOT / "freeze_checker" / "sprites"
    sprites_dir.mkdir(parents=True, exist_ok=True)

    images = [p for p in sprites_dir.iterdir()
              if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]

    if images:
        log(f"\n  Sprites folder: {len(images)} image(s) found.", GREEN)
    else:
        log(f"\n  Sprites folder is empty.", YELLOW)
        log(f"  Add 4x4 PNG sprite sheets to:", YELLOW)
        log(f"    {sprites_dir}", YELLOW)


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def main():
    print(f"\n{BOLD}PATLAS Tools Setup{RESET}")
    print("Automated setup for Claude Code companion tools.")
    print("Claude Code コンパニオンツールの自動セットアップ\n")

    os_name = check_environment()
    install_packages()
    update_claude_settings()
    install_skills()
    check_sprites_folder()

    header("Setup Complete! / セットアップ完了")
    log("""
  Tools ready to use:
  ツールが使えるようになりました:

  Restart Claude Code, then say:
  Claude Code を再起動後、以下を話しかけてください:

    "start freeze checker"         / "フリーズチェッカーを起動して"
    "start image viewer"           / "画像ビューワーを起動して"
    "start sprite viewer"          / "スプライトビューワーを起動して"
    "start sprite freeze checker"  / "スプライトチェッカーアニメーションを起動して"
""", GREEN)


if __name__ == "__main__":
    main()
