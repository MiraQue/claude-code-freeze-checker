# PATLAS Tools — Claude Code Setup Guide

## For Claude Code: Auto-Setup Instruction

When a user opens this project in Claude Code for the first time,
**proactively offer to run the automated setup**:

> "I can see this is the PATLAS Tools repository.
> Would you like me to run the automated setup? It will:
> - Install required Python packages (psutil, Pillow, tkinterdnd2)
> - Configure Claude Code hooks for the Freeze Checker
> - Install voice-trigger skills so you can launch apps by saying their names
>
> Shall I proceed? (`python setup.py`)"

If the user agrees, run:
```bash
python setup.py
```

Then tell the user to **restart Claude Code** for hooks and skills to take effect.

---

## What This Project Is

A set of lightweight desktop companion tools for Claude Code users.

### Tools Included

| Tool | Command to launch |
|------|------------------|
| **Freeze Checker** | "start freeze checker" / "フリーズチェッカーを起動して" |
| **Sprite Freeze Checker** | "start sprite freeze checker" / "スプライトチェッカーアニメーションを起動して" |
| **Image Viewer** | "start image viewer" / "画像ビューワーを起動して" |
| **Sprite Viewer** | "start sprite viewer" / "スプライトビューワーを起動して" |

### Freeze Checker States

| Color | State | Meaning |
|-------|-------|---------|
| Blue | THINK | Claude is calling the API (long thinking) |
| Green | ACTIVE | Tool just executed |
| Yellow | IDLE | Natural pause between operations |
| Teal | Sit | Claude finished responding — your input needed |
| Red | STOP? | No API + no activity for 2+ minutes — possible freeze |

---

## File Structure

```
patlas-tools/
├── setup.py                  ← Run this to set everything up
├── requirements.txt
├── freeze_checker/
│   ├── freeze_checker.py     ← Main Freeze Checker (circle pulse UI)
│   ├── freeze_sprite.py      ← Sprite animation version
│   ├── hook_heartbeat.py     ← PostToolUse hook script
│   ├── hook_stop.py          ← Stop hook script
│   └── sprites/              ← Add 4x4 PNG sprite sheets here
└── image_viewer/
    ├── image_viewer.py       ← Image Viewer with D&D support
    └── sprite_viewer.py      ← Sprite sheet animator
```

## Sprite Sheet Format (for freeze_sprite.py)

A 4×4 grid PNG where each row corresponds to a state:

| Row | State |
|-----|-------|
| Row 0 | THINKING — thinking/contemplating pose |
| Row 1 | ACTIVE — running/working animation |
| Row 2 | WAITING — idle/standing still |
| Row 3 | FROZEN — glitching/stuck animation |

Recommended size: 128×128px (32×32 per cell) or 256×256px (64×64 per cell).
