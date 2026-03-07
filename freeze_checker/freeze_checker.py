"""
freeze_checker.py - Claude Code Freeze Checker v3

Always-on-top window showing Claude Code state in real time.
- Draggable
- Subtle pulse animation
- Stylish HUD design with state text inside circle

States:
    THINKING  (blue)  - API call active
    ACTIVE    (green) - Tool just executed
    IDLE      (yellow)- Short natural pause
    WAITING   (teal)  - Claude finished, your input needed
    FROZEN    (red)   - No activity for 2+ min

Dependencies: pip install psutil
"""

import tkinter as tk
import threading
import time
import json
import socket
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# ---- Config ----
HEARTBEAT_FILE = Path.home() / ".claude" / "freeze_checker_heartbeat.json"
IDLE_THRESHOLD_SEC   = 60
FROZEN_THRESHOLD_SEC = 120
API_HOST = "api.anthropic.com"

# Pulse settings (small, slow)
PULSE_MIN  = 0.28
PULSE_MAX  = 0.38

PULSE_SPEED = {
    "THINKING": 0.006,
    "ACTIVE":   0.009,
    "IDLE":     0.003,
    "WAITING":  0.002,
    "FROZEN":   0.003,
}

SIZE_PRESETS = {"S": 75, "M": 100, "L": 130}
DEFAULT_SIZE = "S"

BG_COLOR = "#0b0b12"

STATES = {
    "THINKING": {
        "core":  "#2266ff",
        "glow":  "#112244",
        "ring":  "#224488",
        "text":  "#88bbff",
        "label": "THINK",
    },
    "ACTIVE": {
        "core":  "#22bb44",
        "glow":  "#112211",
        "ring":  "#226633",
        "text":  "#88ffaa",
        "label": "ACTIVE",
    },
    "IDLE": {
        "core":  "#cc8800",
        "glow":  "#221a00",
        "ring":  "#664400",
        "text":  "#ffcc66",
        "label": "IDLE",
    },
    "WAITING": {
        "core":  "#00bb88",
        "glow":  "#003322",
        "ring":  "#007755",
        "text":  "#aaffdd",
        "label": "Sit",
    },
    "FROZEN": {
        "core":  "#cc2222",
        "glow":  "#220808",
        "ring":  "#661111",
        "text":  "#ff8888",
        "label": "STOP?",
    },
}


def get_api_connection_active() -> bool:
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
                if "node" not in proc.info["name"].lower() and "claude" not in proc.info["name"].lower():
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


class FreezeChecker:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG_COLOR)

        self._size_name = DEFAULT_SIZE
        self._size = SIZE_PRESETS[DEFAULT_SIZE]
        self._state = "WAITING"
        self._radius = (PULSE_MIN + PULSE_MAX) / 2
        self._growing = True
        self._hb_status: str = "waiting"
        self._last_tool_time: float = 0.0

        self._drag_x = 0
        self._drag_y = 0

        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{self._size}x{self._size}+{sw - self._size - 16}+16")

        self._build_ui()
        self._build_menu()
        self._start_monitor()
        self._animate()

    def _build_ui(self):
        s = self._size
        self.canvas = tk.Canvas(
            self.root, width=s, height=s,
            bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack()

        cx = s / 2
        pad = s * 0.04

        self._ring = self.canvas.create_oval(
            pad, pad, s - pad, s - pad,
            outline=STATES["WAITING"]["ring"], width=1, fill=""
        )

        gr = s * 0.42
        self._glow = self.canvas.create_oval(
            cx - gr, cx - gr, cx + gr, cx + gr,
            fill=STATES["WAITING"]["glow"], outline=""
        )

        r = s * self._radius
        self._core = self.canvas.create_oval(
            cx - r, cx - r, cx + r, cx + r,
            fill=STATES["WAITING"]["core"], outline=""
        )

        font_size = max(7, s // 9)
        self._text = self.canvas.create_text(
            cx, cx,
            text=STATES["WAITING"]["label"],
            fill=STATES["WAITING"]["text"],
            font=("Consolas", font_size, "bold")
        )

        self.canvas.bind("<Button-1>",  self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<Button-3>",  self._show_menu)

    def _rebuild_ui(self):
        self.canvas.destroy()
        s = self._size
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{s}x{s}+{x}+{y}")
        self._build_ui()

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def _build_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0,
                            bg="#1a1a2e", fg="#aaaacc",
                            activebackground="#2a2a4e",
                            activeforeground="#ffffff",
                            relief="flat")
        size_menu = tk.Menu(self.menu, tearoff=0,
                            bg="#1a1a2e", fg="#aaaacc",
                            activebackground="#2a2a4e",
                            activeforeground="#ffffff")
        for name in SIZE_PRESETS:
            size_menu.add_command(label=name, command=lambda n=name: self._change_size(n))
        self.menu.add_cascade(label="Size", menu=size_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=self.on_close)

    def _show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def _change_size(self, name: str):
        self._size_name = name
        self._size = SIZE_PRESETS[name]
        self._rebuild_ui()

    def _start_monitor(self):
        self._running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while self._running:
            try:
                hb = read_heartbeat()
                ts     = hb.get("timestamp", 0.0)
                status = hb.get("status", "waiting")

                if ts != self._last_tool_time:
                    self._last_tool_time = ts
                self._hb_status = status

                api = get_api_connection_active()
                now = time.time()
                elapsed = now - self._last_tool_time if self._last_tool_time > 0 else float("inf")

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
            except Exception:
                pass
            time.sleep(2)

    def _animate(self):
        info  = STATES[self._state]
        speed = PULSE_SPEED[self._state]
        s     = self._size
        cx    = s / 2

        if self._growing:
            self._radius += speed
            if self._radius >= PULSE_MAX:
                self._growing = False
        else:
            self._radius -= speed
            if self._radius <= PULSE_MIN:
                self._growing = True

        r = s * self._radius
        self.canvas.coords(self._core, cx - r, cx - r, cx + r, cx + r)
        self.canvas.itemconfig(self._core, fill=info["core"])
        self.canvas.itemconfig(self._glow, fill=info["glow"])
        self.canvas.itemconfig(self._ring, outline=info["ring"])
        self.canvas.itemconfig(self._text, text=info["label"], fill=info["text"])

        self.root.after(50, self._animate)

    def on_close(self):
        self._running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FreezeChecker(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
