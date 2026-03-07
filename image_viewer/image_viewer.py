"""
image_viewer.py - Image Viewer

Dark-themed image viewer with drag & drop support.
Navigate images in the same folder with arrow keys.
Zoom with mouse wheel.

Dependencies: pip install Pillow tkinterdnd2
"""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    TkinterDnD = None
    DND_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".ico"}

BG          = "#0b0b12"
BG_STATUS   = "#0e0e18"
BG_HINT     = "#0d0d1a"
FG          = "#aaaacc"
FG_DIM      = "#445566"
FG_ACCENT   = "#4488ff"
FG_ERROR    = "#ff6666"
FG_WARN     = "#ffaa44"
BORDER      = "#223344"


class ImageViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Image Viewer")
        self.root.configure(bg=BG)
        self.root.geometry("960x680")
        self.root.minsize(400, 300)

        self._image_list = []
        self._current_index = 0
        self._pil_image = None
        self._photo = None

        self._fit = True
        self._zoom = 1.0
        self._pan_x = 0
        self._pan_y = 0
        self._pan_origin = None
        self._pan_base = (0, 0)

        self._build_menu()
        self._build_canvas()
        self._build_statusbar()
        self._bind_keys()

        if not PIL_AVAILABLE:
            self._show_message(
                "Pillow is not installed",
                "Run: pip install Pillow",
                color=FG_ERROR
            )
        elif not DND_AVAILABLE:
            self._show_message(
                "To enable drag & drop:",
                "Run: pip install tkinterdnd2  then restart\n(You can still open files with Ctrl+O)",
                color=FG_WARN
            )
            self._setup_hint_delayed()
        else:
            self._setup_dnd()
            self._setup_hint_delayed()

    def _build_menu(self):
        menu_cfg = dict(bg="#12121e", fg=FG, activebackground="#1e1e38",
                        activeforeground="white", relief="flat", bd=0)
        menubar = tk.Menu(self.root, **menu_cfg)

        file_menu = tk.Menu(menubar, tearoff=0, **menu_cfg)
        file_menu.add_command(label="Open…",       command=self._open_dialog,          accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Prev image",  command=lambda: self._navigate(-1), accelerator="←")
        file_menu.add_command(label="Next image",  command=lambda: self._navigate(1),  accelerator="→")
        file_menu.add_separator()
        file_menu.add_command(label="Close",       command=self.root.destroy,          accelerator="Ctrl+W")
        menubar.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=0, **menu_cfg)
        view_menu.add_command(label="Fit to window",   command=self._fit_to_window,          accelerator="F")
        view_menu.add_command(label="Actual size 100%", command=self._actual_size,            accelerator="1")
        view_menu.add_separator()
        view_menu.add_command(label="Zoom in  (+20%)", command=lambda: self._zoom_step(1.2), accelerator="+")
        view_menu.add_command(label="Zoom out (-20%)", command=lambda: self._zoom_step(0.8), accelerator="-")
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=menubar)

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self.root, bg=BG, highlightthickness=0, cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=BG_STATUS, height=22)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        sep = tk.Frame(self.root, bg="#1a1a2e", height=1)
        sep.pack(fill="x", side="bottom")

        self._st_left  = tk.Label(bar, text="", bg=BG_STATUS, fg=FG_DIM,
                                  font=("Consolas", 8), anchor="w", padx=10)
        self._st_left.pack(side="left", fill="y")

        self._st_right = tk.Label(bar, text="", bg=BG_STATUS, fg=FG_DIM,
                                  font=("Consolas", 8), anchor="e", padx=10)
        self._st_right.pack(side="right", fill="y")

    def _bind_keys(self):
        self.root.bind("<Control-o>",  lambda e: self._open_dialog())
        self.root.bind("<Control-w>",  lambda e: self.root.destroy())
        self.root.bind("<Left>",       lambda e: self._navigate(-1))
        self.root.bind("<Right>",      lambda e: self._navigate(1))
        self.root.bind("<f>",          lambda e: self._fit_to_window())
        self.root.bind("<F>",          lambda e: self._fit_to_window())
        self.root.bind("<1>",          lambda e: self._actual_size())
        self.root.bind("<plus>",       lambda e: self._zoom_step(1.2))
        self.root.bind("<equal>",      lambda e: self._zoom_step(1.2))
        self.root.bind("<minus>",      lambda e: self._zoom_step(0.8))
        self.canvas.bind("<Configure>",     self._on_resize)
        self.canvas.bind("<MouseWheel>",    self._on_wheel)
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>",     self._pan_move)
        self.canvas.bind("<ButtonPress-3>", self._pan_start)
        self.canvas.bind("<B3-Motion>",     self._pan_move)

    def _setup_dnd(self):
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        image_paths = [p for p in paths if Path(p).suffix.lower() in IMAGE_EXT]
        if image_paths:
            self._load_file(image_paths[0])

    def _open_dialog(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp *.tiff *.tif *.ico"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        p = Path(path)
        if not p.exists() or p.suffix.lower() not in IMAGE_EXT:
            return

        try:
            img = Image.open(str(p))
            img.load()
            self._pil_image = img
        except Exception as e:
            self._show_message("Load error", str(e), color=FG_ERROR)
            return

        folder = p.parent
        self._image_list = sorted(
            [f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXT],
            key=lambda f: f.name.lower()
        )
        try:
            self._current_index = self._image_list.index(p)
        except ValueError:
            self._image_list = [p]
            self._current_index = 0

        self._fit   = True
        self._zoom  = 1.0
        self._pan_x = 0
        self._pan_y = 0
        self.root.title(f"Image Viewer  —  {p.name}")
        self._render()

    def _navigate(self, direction: int):
        if not self._image_list:
            return
        idx = (self._current_index + direction) % len(self._image_list)
        if idx != self._current_index:
            self._load_file(str(self._image_list[idx]))

    def _render(self):
        if self._pil_image is None:
            return
        self.canvas.delete("all")

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        iw, ih = self._pil_image.size

        if self._fit:
            ratio = min(cw / iw, ch / ih)
            dw, dh = max(1, int(iw * ratio)), max(1, int(ih * ratio))
        else:
            dw, dh = max(1, int(iw * self._zoom)), max(1, int(ih * self._zoom))
            ratio   = self._zoom

        resized      = self._pil_image.resize((dw, dh), Image.LANCZOS)
        self._photo  = ImageTk.PhotoImage(resized)

        cx = cw // 2 + self._pan_x
        cy = ch // 2 + self._pan_y
        self.canvas.create_image(cx, cy, anchor="center", image=self._photo)

        if len(self._image_list) > 1:
            self._draw_nav_arrows(cw, ch)

        idx_str  = f"{self._current_index + 1}  /  {len(self._image_list)}"
        zoom_pct = f"{int(ratio * 100)} %"
        self._st_left.config(
            text=f"  {self._image_list[self._current_index].name}    {idx_str}"
        )
        self._st_right.config(
            text=f"{iw} × {ih} px    {zoom_pct}  "
        )

    def _draw_nav_arrows(self, cw: int, ch: int):
        cy = ch // 2
        pad = 14
        self.canvas.create_polygon(
            pad + 12, cy,
            pad, cy - 10,
            pad, cy + 10,
            fill="#2a2a44", outline=""
        )
        self.canvas.create_polygon(
            cw - pad - 12, cy,
            cw - pad, cy - 10,
            cw - pad, cy + 10,
            fill="#2a2a44", outline=""
        )

    def _setup_hint_delayed(self):
        self.root.after(100, self._show_empty_hint)

    def _show_empty_hint(self):
        if self._pil_image is not None:
            return
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()  or 960
        ch = self.canvas.winfo_height() or 680
        cx, cy = cw // 2, ch // 2
        pad = 80

        self.canvas.create_rectangle(
            pad, pad, cw - pad, ch - pad,
            outline=BORDER, width=1, dash=(8, 6), fill=BG_HINT
        )
        r = 28
        self.canvas.create_oval(cx - r, cy - r - 22, cx + r, cy + r - 22,
                                outline="#334466", width=1, fill="")
        self.canvas.create_line(cx, cy - r - 22, cx, cy - 10,
                                fill="#334466", width=1)

        self.canvas.create_text(cx, cy + 12,
                                text="Drop an image here",
                                fill="#3a5a7a", font=("Segoe UI", 18, "bold"))
        self.canvas.create_text(cx, cy + 44,
                                text="or  Ctrl + O  to open a file",
                                fill=FG_DIM, font=("Segoe UI", 10))
        self.canvas.create_text(cx, cy + 66,
                                text="← →  navigate folder   /   Mouse wheel to zoom",
                                fill=FG_DIM, font=("Segoe UI", 9))

        self._st_left.config(text="")
        self._st_right.config(text="")

    def _show_message(self, title: str, body: str, color: str = FG):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()  or 960
        ch = self.canvas.winfo_height() or 680
        cx, cy = cw // 2, ch // 2
        self.canvas.create_text(cx, cy - 14, text=title, fill=color,
                                font=("Segoe UI", 13, "bold"), justify="center")
        self.canvas.create_text(cx, cy + 18, text=body,  fill=FG_DIM,
                                font=("Consolas", 10), justify="center")

    def _fit_to_window(self):
        self._fit   = True
        self._pan_x = 0
        self._pan_y = 0
        self._render()

    def _actual_size(self):
        self._fit   = False
        self._zoom  = 1.0
        self._pan_x = 0
        self._pan_y = 0
        self._render()

    def _zoom_step(self, factor: float):
        self._fit  = False
        self._zoom = max(0.05, min(self._zoom * factor, 32.0))
        self._render()

    def _on_wheel(self, event):
        if event.delta > 0:
            self._zoom_step(1.15)
        else:
            self._zoom_step(1 / 1.15)

    def _pan_start(self, event):
        self._pan_origin = (event.x, event.y)
        self._pan_base   = (self._pan_x, self._pan_y)

    def _pan_move(self, event):
        if self._pan_origin is None:
            return
        dx = event.x - self._pan_origin[0]
        dy = event.y - self._pan_origin[1]
        self._pan_x = self._pan_base[0] + dx
        self._pan_y = self._pan_base[1] + dy
        self._fit   = False
        self._render()

    def _on_resize(self, event):
        if self._pil_image is not None:
            self._render()
        else:
            self._show_empty_hint()


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    root.configure(bg=BG)
    app = ImageViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
