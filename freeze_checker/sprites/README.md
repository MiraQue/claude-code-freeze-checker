# Sprite Sheets for Freeze Sprite Checker

Place 4×4 PNG sprite sheets here.

## Format

| Grid | Meaning |
|------|---------|
| 4 columns | 4 animation frames per state |
| 4 rows | 4 states |

## Row → State mapping

| Row | Claude Code State |
|-----|------------------|
| Row 0 | THINKING — API active (long thinking) |
| Row 1 | ACTIVE — tool executing |
| Row 2 | WAITING / IDLE — user input needed, or short pause |
| Row 3 | FROZEN — no activity for 2+ minutes |

## Recommended size

- 128×128 px (32×32 per cell) — default
- 256×256 px (64×64 per cell) — high DPI

PNG with transparency works best.
