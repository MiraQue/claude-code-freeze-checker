"""
freeze_sprite.py - Sprite Freeze Checker

Shows Claude Code state as an animated character sprite.
Uses a 4×4 sprite sheet from the sprites/ folder.

Usage:
    python freeze_sprite.py          # last used sprite, or first one
    python freeze_sprite.py 1        # 1st sprite in sprites/ (1-indexed)
    python freeze_sprite.py 3        # 3rd sprite in sprites/

Row → State mapping:
    Row 0 = THINKING (API active)
    Row 1 = ACTIVE   (tool executing)
    Row 2 = WAITING  (user input needed) / IDLE
    Row 3 = FROZEN   (possible freeze)

Dependencies: pip install Pillow psutil
"""

import sys
import tkinter as tk
from pathlib import Path
import threading
import time
import json
import socket

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ---- Paths ----
SPRITES_DIR    = Path(__file__).parent / "sprites"
CONFIG_FILE    = Path.home() / ".claude" / "freeze_sprite_config.json"
HEARTBEAT_FILE = Path.home() / ".claude" / "freeze_checker_heartbeat.json"
API_HOST       = "api.anthropic.com"
IMAGE_EXT      = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

IDLE_THRESHOLD_SEC   = 60
FROZEN_THRESHOLD_SEC = 120
SPRITE_COLS = 4
SPRITE_ROWS = 4

STATE_ROW = {
    "THINKING": 0,
    "ACTIVE":   1,
    "WAITING":  2,
    "IDLE":     2,
    "FROZEN":   3,
}
STATE_FPS = {
    "THINKING": 200,
    "ACTIVE":   100,
    "WAITING":  500,
    "IDLE":     600,
    "FROZEN":   350,
}
STATE_COLOR = {
    "THINKING": "#4488ff",
    "ACTIVE":   "#44cc44",
    "WAITING":  "#00bb88",
    "IDLE":     "#cc8800",
    "FROZEN":   "#cc2222",
}

SIZE_PRESETS = {"S": 64, "M": 96, "L": 128}
DEFAULT_SIZE = "M"


def list_sprites() -> list:
    if not SPRITES_DIR.exists():
        return []
    return sorted(
        [p for p in SPRITES_DIR.iterdir()
         if p.suffix.lower() in IMAGE_EXT],
        key=lambda p: p.name.lower()
    )


def get_api_active() -> bool:
    if not PSUTIL_AVAILABLE:
        return False
    try:
        api_ips = set()
        try:
            for r in socket.getaddrinfo(API_HOST, 443, proto=socket.IPPROTO_TCP):
                api_ips.add(r[4][0])
        except Exception:
            pass
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"].lower()
                if "node" not in name and "claude" not in name:
                    continue
                for c in proc.net_connections(kind="tcp"):
                    if c.status == "ESTABLISHED" and c.raddr:
                        if c.raddr.ip in api_ips or c.raddr.port == 443:
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return False


def read_heartbeat() -> dict:
    try:
        if HEARTBEAT_FILE.exists():
            with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def load_config() -> dict:
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(data: dict):
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


class FreezeSpriteChecker:
    def __init__(self, root: tk.Tk, initial_index: int = 0):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#000000")

        self._size_name = DEFAULT_SIZE
        self._size      = SIZE_PRESETS[DEFAULT_SIZE]
        self._state     = "WAITING"
        self._frame_idx = 0
        self._anim_id   = None

        self._sprite_list = list_sprites()
        self._sprite_index = 0
        self._frames = []
        self._photos = []

        self._last_tool_time: float = 0.0
        self._hb_status: str = "waiting"
        self._monitor_running = True

        self._drag_x = 0
        self._drag_y = 0

        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{self._size}x{self._size}+{sw - self._size - 16}+90")

        self._build_ui()
        self._build_menu()
        self._resolve_initial_sprite(initial_index)
        self._start_monitor()
        self._animate()

    def _resolve_initial_sprite(self, initial_index: int):
        sprites = self._sprite_list
        if not sprites:
            return

        if 0 < initial_index <= len(sprites):
            self._sprite_index = initial_index - 1
        else:
            cfg = load_config()
            last_name = cfg.get("sprite_name", "")
            names = [p.name for p in sprites]
            if last_name in names:
                self._sprite_index = names.index(last_name)
            else:
                self._sprite_index = 0

        self._load_sprite_by_index(self._sprite_index)

    def _build_ui(self):
        s = self._size
        self.canvas = tk.Canvas(
            self.root, width=s, height=s,
            bg="#000000", highlightthickness=0
        )
        self.canvas.pack()

        self._oval = self.canvas.create_oval(
            s * 0.1, s * 0.1, s * 0.9, s * 0.9,
            fill=STATE_COLOR["WAITING"], outline=""
        )
        self._label = self.canvas.create_text(
            s // 2, s // 2, text="WAIT",
            fill="white", font=("Consolas", max(7, s // 9), "bold")
        )
        self._sprite_img = None

        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>",     self._drag_move)
        self.canvas.bind("<Button-3>",      self._show_menu)

    def _rebuild_ui(self):
        self.canvas.destroy()
        s = self._size
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{s}x{s}+{x}+{y}")
        self._build_ui()
        self._photos = []
        if self._frames:
            self._cache_row_photos()

    def _load_sprite_by_index(self, idx: int):
        sprites = self._sprite_list
        if not sprites or idx < 0 or idx >= len(sprites):
            return
        self._sprite_index = idx
        path = sprites[idx]
        try:
            img = Image.open(str(path)).convert("RGBA")
            iw, ih = img.size
            fw, fh = iw // SPRITE_COLS, ih // SPRITE_ROWS
            self._frames = []
            for row in range(SPRITE_ROWS):
                row_frames = []
                for col in range(SPRITE_COLS):
                    x0, y0 = col * fw, row * fh
                    row_frames.append(img.crop((x0, y0, x0 + fw, y0 + fh)))
                self._frames.append(row_frames)
            self._cache_row_photos()
            self._frame_idx = 0
            save_config({"sprite_name": path.name})
        except Exception:
            pass

    def _cache_row_photos(self):
        if not self._frames:
            return
        row = STATE_ROW.get(self._state, 2)
        row = min(row, len(self._frames) - 1)
        s = self._size
        self._photos = []
        for frame in self._frames[row]:
            resized = frame.resize((s, s), Image.NEAREST)
            self._photos.append(ImageTk.PhotoImage(resized))

    def _switch_sprite(self, direction: int):
        self._sprite_list = list_sprites()
        if not self._sprite_list:
            return
        new_idx = (self._sprite_index + direction) % len(self._sprite_list)
        self._photos = []
        if self._sprite_img:
            self.canvas.delete(self._sprite_img)
            self._sprite_img = None
        self._load_sprite_by_index(new_idx)

    def _build_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0,
                            bg="#12121e", fg="#aaaacc",
                            activebackground="#1e1e38",
                            activeforeground="#ffffff", relief="flat")

        self.sprite_menu = tk.Menu(self.menu, tearoff=0,
                                   bg="#12121e", fg="#aaaacc",
                                   activebackground="#1e1e38",
                                   activeforeground="#ffffff")
        self.menu.add_cascade(label="Select Sprite", menu=self.sprite_menu)
        self.menu.add_command(label="◀ Prev",
                              command=lambda: self._switch_sprite(-1))
        self.menu.add_command(label="▶ Next",
                              command=lambda: self._switch_sprite(1))
        self.menu.add_separator()

        size_menu = tk.Menu(self.menu, tearoff=0,
                            bg="#12121e", fg="#aaaacc",
                            activebackground="#1e1e38",
                            activeforeground="#ffffff")
        for name in SIZE_PRESETS:
            size_menu.add_command(label=name,
                                  command=lambda n=name: self._change_size(n))
        self.menu.add_cascade(label="Size", menu=size_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=self.on_close)

    def _show_menu(self, event):
        self.sprite_menu.delete(0, "end")
        sprites = list_sprites()
        if sprites:
            for i, p in enumerate(sprites):
                label = f"{i + 1}. {p.name}"
                if i == self._sprite_index:
                    label = "✓ " + label
                self.sprite_menu.add_command(
                    label=label,
                    command=lambda idx=i: self._load_sprite_by_index(idx)
                )
        else:
            self.sprite_menu.add_command(
                label="Add PNG files to sprites/ folder",
                state="disabled"
            )
        self.menu.post(event.x_root, event.y_root)

    def _change_size(self, name: str):
        self._size_name = name
        self._size = SIZE_PRESETS[name]
        self._rebuild_ui()

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def _start_monitor(self):
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while self._monitor_running:
            try:
                hb      = read_heartbeat()
                ts      = hb.get("timestamp", 0.0)
                status  = hb.get("status", "waiting")
                if ts != self._last_tool_time:
                    self._last_tool_time = ts
                self._hb_status = status

                api     = get_api_active()
                now     = time.time()
                elapsed = now - self._last_tool_time if self._last_tool_time > 0 else float("inf")

                prev = self._state
                if status == "waiting":
                    # Stop hook takes priority: response complete = user input needed
                    self._state = "WAITING"
                elif api:
                    self._state = "THINKING"
                elif elapsed < 5:
                    self._state = "ACTIVE"
                elif elapsed < IDLE_THRESHOLD_SEC:
                    self._state = "IDLE"
                elif elapsed >= FROZEN_THRESHOLD_SEC:
                    self._state = "FROZEN"
                else:
                    self._state = "IDLE"

                if self._state != prev and self._frames:
                    self._cache_row_photos()
                    self._frame_idx = 0
            except Exception:
                pass
            time.sleep(2)

    def _animate(self):
        if self._anim_id:
            self.root.after_cancel(self._anim_id)
        self._draw_frame()
        delay = STATE_FPS.get(self._state, 300)
        self._anim_id = self.root.after(delay, self._animate)

    def _draw_frame(self):
        s = self._size
        if self._photos:
            photo = self._photos[self._frame_idx % len(self._photos)]
            self._frame_idx = (self._frame_idx + 1) % len(self._photos)
            if self._sprite_img is None:
                self.canvas.itemconfig(self._oval,  state="hidden")
                self.canvas.itemconfig(self._label, state="hidden")
                self._sprite_img = self.canvas.create_image(
                    s // 2, s // 2, anchor="center", image=photo
                )
            else:
                self.canvas.itemconfig(self._sprite_img, image=photo)
            self.canvas.image = photo
        else:
            color = STATE_COLOR.get(self._state, "#555566")
            self.canvas.itemconfig(self._oval,  fill=color, state="normal")
            self.canvas.itemconfig(self._label,
                                   text=self._state[:4], state="normal")
            if self._sprite_img:
                self.canvas.delete(self._sprite_img)
                self._sprite_img = None

    def on_close(self):
        self._monitor_running = False
        if self._anim_id:
            self.root.after_cancel(self._anim_id)
        self.root.destroy()


def main():
    if not PIL_AVAILABLE:
        print("Pillow is required: pip install Pillow")
        return

    initial_index = 0
    if len(sys.argv) > 1:
        try:
            initial_index = int(sys.argv[1])
        except ValueError:
            pass

    root = tk.Tk()
    app = FreezeSpriteChecker(root, initial_index=initial_index)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
