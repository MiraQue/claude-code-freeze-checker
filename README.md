# Claude Code Freeze Checker

Real-time activity monitor for [Claude Code](https://claude.ai/code) — see at a glance whether Claude is thinking, working, waiting, or frozen.

> Part of **claude-code-tools** series by [MiraQue](https://github.com/MiraQue)

> **日本語の説明は下部にあります / Japanese README is below.**

---

## Tools

### Freeze Checker
A small always-on-top window that shows Claude Code's current state in real time — so you can tell at a glance if it's thinking, working, waiting for you, or frozen.

| Color | State | Meaning |
|-------|-------|---------|
| 🔵 Blue | THINK | Claude is calling the API — long thinking (normal) |
| 🟢 Green | ACTIVE | A tool just executed |
| 🟡 Yellow | IDLE | Short natural pause |
| 🩵 Teal | Sit | Claude finished — your input needed |
| 🔴 Red | STOP? | No API + no activity for 2+ min — possible freeze |

### Sprite Freeze Checker
The same Freeze Checker, but instead of a colored dot it animates a character sprite. Drop any 4×4 pixel-art sprite sheet into the `sprites/` folder.

### Image Viewer
A clean dark-themed image viewer with drag & drop support. Navigate through images in the same folder with arrow keys. Zoom with mouse wheel.

### Sprite Viewer
A sprite sheet animator. Drop a sprite sheet, choose rows, set frame rate, and play back animations — useful for checking how sprites look before using them in a game.

---

## Requirements

- Python 3.9+
- Claude Code

---

## Installation

### 1. Clone this repository

```bash
git clone https://github.com/MiraQue/claude-code-freeze-checker.git
cd patlas-tools
```

### 2. Open the folder in Claude Code

```bash
claude patlas-tools/
```

Claude Code will read `CLAUDE.md` and **automatically offer to run setup**.
Just say **"yes"** or **"OK"**.

### 3. Manual setup (alternative)

If you prefer to set up manually:

```bash
python setup.py
```

This will:
- Install required Python packages (`psutil`, `Pillow`, `tkinterdnd2`)
- Add Claude Code hooks to `~/.claude/settings.json`
- Install voice-trigger skills for each tool

### 4. Restart Claude Code

Hooks and skills take effect after a restart.

---

## Usage

After setup, launch tools by talking to Claude Code:

| Tool | English | 日本語 |
|------|---------|--------|
| Freeze Checker | "start freeze checker" | "フリーズチェッカーを起動して" |
| Sprite Checker | "start sprite freeze checker" | "スプライトチェッカーアニメーションを起動して" |
| Image Viewer | "start image viewer" | "画像ビューワーを起動して" |
| Sprite Viewer | "start sprite viewer" | "スプライトビューワーを起動して" |

### Freeze Checker controls
- **Drag** to move the window
- **Right-click** to change size or close

### Image Viewer controls
- **Drop** image files onto the window
- **← →** to navigate images in the same folder
- **Mouse wheel** to zoom
- **Right-click drag** to pan
- **F** to fit to window

### Sprite Viewer controls
- **Drop** a sprite sheet
- Select **row** (animation type) with buttons
- **Space** to play/stop, **→** to step frame
- Adjust **speed slider** and **grid settings**

---

## Sprite Sheet Format (for Sprite Freeze Checker)

A 4×4 grid image where rows map to Claude Code states:

| Row | Claude Code state |
|-----|------------------|
| Row 0 | THINKING (API active) |
| Row 1 | ACTIVE (tool executing) |
| Row 2 | WAITING (your input needed) |
| Row 3 | FROZEN (possible freeze) |

Recommended: 128×128 px PNG with transparency (32×32 per cell).

Place sprite sheets in `freeze_checker/sprites/`.

---

## macOS Notes

tkinter may require a separate install:
```bash
brew install python-tk
```

---

## License

MIT

---
---

# 日本語 README

## 概要

Claude Code のフリーズチェッカー -- 動作状態をリアルタイム表示する常駐モニターです。

> **claude-code-tools** シリーズ（[MiraQue](https://github.com/MiraQue)）

## ツール一覧

| ツール | 説明 |
|--------|------|
| **フリーズチェッカー** | Claude Code の動作状態をリアルタイムで表示する常駐ウィンドウ |
| **スプライトフリーズチェッカー** | フリーズチェッカーのキャラクターアニメーション版 |
| **画像ビューワー** | ドラッグ&ドロップ対応のダークテーマ画像表示アプリ |
| **スプライトビューワー** | スプライトシートのアニメーション確認ツール |

## インストール手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/MiraQue/claude-code-freeze-checker.git
```

### 2. Claude Code でフォルダを開く

```bash
claude patlas-tools/
```

Claude Code が `CLAUDE.md` を読み込み、**自動でセットアップを提案**します。
「はい」または「OK」と答えるだけです。

### 3. 手動セットアップ（代替）

```bash
python setup.py
```

### 4. Claude Code を再起動

フックとスキルを有効にするため再起動してください。

## 使い方

セットアップ後は Claude Code に話しかけるだけで起動できます：

- 「フリーズチェッカーを起動して」
- 「画像ビューワーを起動して」
- 「スプライトビューワーを起動して」
- 「スプライトチェッカーアニメーションを起動して」

## フリーズチェッカーの状態

| 色 | 状態 | 意味 |
|----|------|------|
| 青 | THINK | API通信中（長考中） |
| 緑 | ACTIVE | ツール実行直後 |
| 黄 | IDLE | 短い待機（正常） |
| 緑青 | Sit | 返答完了・あなたの入力待ち |
| 赤 | STOP? | 2分以上無応答（フリーズ疑い） |
