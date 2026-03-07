"""
sprite_viewer.py - Sprite Sheet Animator

Load a sprite sheet (N columns × M rows), select a row, play animation.

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

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

BG          = "#0b0b12"
BG_PANEL    = "#0e0e1a"
BG_STATUS   = "#0e0e18"
BG_THUMB    = "#12121e"
BG_THUMB_HL = "#1a2244"
FG          = "#aaaacc"
FG_DIM      = "#445566"
FG_ACCENT   = "#4488ff"
FG_ACTIVE   = "#ffffff"
FG_ERROR    = "#ff6666"
BORDER      = "#1e1e33"
BTN_BG      = "#1a1a2e"
BTN_ACT     = "#2a2a55"

THUMB_SIZE  = 64
DISPLAY_MIN = 200


class SpriteViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sprite Viewer")
        self.root.configure(bg=BG)
        self.root.geometry("900x680")
        self.root.minsize(600, 500)

        self._pil_full = None
        self._frames = []
        self._cols = 4
        self._rows = 4
        self._current_row   = 0
        self._current_frame = 0

        self._playing    = False
        self._anim_id    = None
        self._frame_ms   = 150

        self._display_photo = None
        self._thumb_photos  = []

        self._build_ui()
        self._bind_keys()

        if not PIL_AVAILABLE:
            self._set_status("Pillow is not installed. Run: pip install Pillow", error=True)
        elif DND_AVAILABLE:
            self._setup_dnd()

        self._show_empty_hint()

    def _build_ui(self):
        self._main_frame = tk.Frame(self.root, bg=BG)
        self._main_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._main_frame, bg=BG, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        self._thumb_frame = tk.Frame(self.root, bg=BG_PANEL, height=THUMB_SIZE + 16)
        self._thumb_frame.pack(fill="x")
        self._thumb_frame.pack_propagate(False)

        self._thumb_canvas = tk.Canvas(
            self._thumb_frame, bg=BG_PANEL, height=THUMB_SIZE + 16,
            highlightthickness=0
        )
        self._thumb_canvas.pack(fill="x", padx=8, pady=4)

        ctrl = tk.Frame(self.root, bg=BG_PANEL, pady=6)
        ctrl.pack(fill="x")

        sep = tk.Frame(self.root, bg=BORDER, height=1)
        sep.pack(fill="x", before=ctrl)

        # Row selector
        row_sect = tk.Frame(ctrl, bg=BG_PANEL)
        row_sect.pack(side="left", padx=12)

        tk.Label(row_sect, text="Row", bg=BG_PANEL, fg=FG_DIM,
                 font=("Consolas", 9)).pack(side="left", padx=(0, 4))

        self._row_buttons = []
        self._row_btn_frame = tk.Frame(row_sect, bg=BG_PANEL)
        self._row_btn_frame.pack(side="left")

        # Playback controls
        play_sect = tk.Frame(ctrl, bg=BG_PANEL)
        play_sect.pack(side="left", padx=16)

        self._btn_play = tk.Button(
            play_sect, text="▶  Play", command=self._play,
            bg=BTN_BG, fg=FG_ACCENT, activebackground=BTN_ACT, activeforeground=FG_ACCENT,
            relief="flat", font=("Consolas", 9), padx=10, pady=3, cursor="hand2"
        )
        self._btn_play.pack(side="left", padx=2)

        self._btn_stop = tk.Button(
            play_sect, text="■  Stop", command=self._stop,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACT, activeforeground=FG_ACTIVE,
            relief="flat", font=("Consolas", 9), padx=10, pady=3, cursor="hand2"
        )
        self._btn_stop.pack(side="left", padx=2)

        self._btn_step = tk.Button(
            play_sect, text="▶|", command=self._step_frame,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACT, activeforeground=FG_ACTIVE,
            relief="flat", font=("Consolas", 9), padx=8, pady=3, cursor="hand2"
        )
        self._btn_step.pack(side="left", padx=2)

        # Speed slider
        spd_sect = tk.Frame(ctrl, bg=BG_PANEL)
        spd_sect.pack(side="left", padx=16)

        tk.Label(spd_sect, text="Speed", bg=BG_PANEL, fg=FG_DIM,
                 font=("Consolas", 9)).pack(side="left", padx=(0, 6))

        self._speed_var = tk.IntVar(value=self._frame_ms)
        spd_slider = tk.Scale(
            spd_sect, from_=40, to=600, orient="horizontal",
            variable=self._speed_var, command=self._on_speed_change,
            bg=BG_PANEL, fg=FG, troughcolor=BORDER, highlightthickness=0,
            sliderlength=12, length=100, showvalue=False
        )
        spd_slider.pack(side="left")

        self._spd_label = tk.Label(spd_sect, text=f"{self._frame_ms}ms",
                                   bg=BG_PANEL, fg=FG_DIM, font=("Consolas", 8), width=5)
        self._spd_label.pack(side="left")

        # Grid settings
        grid_sect = tk.Frame(ctrl, bg=BG_PANEL)
        grid_sect.pack(side="left", padx=16)

        tk.Label(grid_sect, text="Grid", bg=BG_PANEL, fg=FG_DIM,
                 font=("Consolas", 9)).pack(side="left", padx=(0, 6))

        tk.Label(grid_sect, text="cols", bg=BG_PANEL, fg=FG_DIM,
                 font=("Consolas", 9)).pack(side="left")
        self._cols_var = tk.StringVar(value="4")
        cols_entry = tk.Entry(grid_sect, textvariable=self._cols_var, width=3,
                              bg=BTN_BG, fg=FG, insertbackground=FG, relief="flat",
                              font=("Consolas", 10))
        cols_entry.pack(side="left", padx=2)

        tk.Label(grid_sect, text="rows", bg=BG_PANEL, fg=FG_DIM,
                 font=("Consolas", 9)).pack(side="left", padx=(6, 0))
        self._rows_var = tk.StringVar(value="4")
        rows_entry = tk.Entry(grid_sect, textvariable=self._rows_var, width=3,
                              bg=BTN_BG, fg=FG, insertbackground=FG, relief="flat",
                              font=("Consolas", 10))
        rows_entry.pack(side="left", padx=2)

        tk.Button(
            grid_sect, text="Apply", command=self._apply_grid,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACT, activeforeground=FG_ACTIVE,
            relief="flat", font=("Consolas", 9), padx=8, pady=3, cursor="hand2"
        ).pack(side="left", padx=6)

        tk.Button(
            ctrl, text="Open…", command=self._open_dialog,
            bg=BTN_BG, fg=FG_DIM, activebackground=BTN_ACT, activeforeground=FG_ACTIVE,
            relief="flat", font=("Consolas", 9), padx=8, pady=3, cursor="hand2"
        ).pack(side="right", padx=12)

        sep2 = tk.Frame(self.root, bg=BORDER, height=1)
        sep2.pack(fill="x")
        status_bar = tk.Frame(self.root, bg=BG_STATUS, height=20)
        status_bar.pack(fill="x")
        status_bar.pack_propagate(False)
        self._status = tk.Label(status_bar, text="", bg=BG_STATUS, fg=FG_DIM,
                                font=("Consolas", 8), anchor="w", padx=10)
        self._status.pack(side="left", fill="y")

        self._canvas.bind("<Configure>", self._on_canvas_resize)

    def _rebuild_row_buttons(self):
        for w in self._row_btn_frame.winfo_children():
            w.destroy()
        self._row_buttons = []
        for i in range(self._rows):
            btn = tk.Button(
                self._row_btn_frame,
                text=str(i),
                command=lambda r=i: self._select_row(r),
                bg=BTN_BG, fg=FG, activebackground=BTN_ACT, activeforeground=FG_ACTIVE,
                relief="flat", font=("Consolas", 9), width=3, pady=3, cursor="hand2"
            )
            btn.pack(side="left", padx=1)
            self._row_buttons.append(btn)
        self._highlight_row_button()

    def _highlight_row_button(self):
        for i, btn in enumerate(self._row_buttons):
            if i == self._current_row:
                btn.config(bg=BTN_ACT, fg=FG_ACCENT)
            else:
                btn.config(bg=BTN_BG, fg=FG)

    def _bind_keys(self):
        self.root.bind("<Control-o>", lambda e: self._open_dialog())
        self.root.bind("<space>",     lambda e: self._toggle_play())
        self.root.bind("<Right>",     lambda e: self._step_frame())
        self.root.bind("<Up>",        lambda e: self._select_row(max(0, self._current_row - 1)))
        self.root.bind("<Down>",      lambda e: self._select_row(min(self._rows - 1, self._current_row + 1)))

    def _setup_dnd(self):
        self._canvas.drop_target_register(DND_FILES)
        self._canvas.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        image_paths = [p for p in paths if Path(p).suffix.lower() in IMAGE_EXT]
        if image_paths:
            self._load_file(image_paths[0])

    def _open_dialog(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"),
                       ("All files", "*.*")]
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        p = Path(path)
        try:
            img = Image.open(str(p)).convert("RGBA")
            img.load()
            self._pil_full = img
        except Exception as e:
            self._set_status(f"Load error: {e}", error=True)
            return

        self.root.title(f"Sprite Viewer  —  {p.name}")
        self._extract_frames()
        self._rebuild_row_buttons()
        self._current_row   = 0
        self._current_frame = 0
        self._update_thumb_strip()
        self._render_main()
        iw, ih = self._pil_full.size
        fw, fh = iw // self._cols, ih // self._rows
        self._set_status(
            f"{p.name}  |  {iw}×{ih}px  |  {self._cols} cols × {self._rows} rows  |  frame {fw}×{fh}px"
        )

    def _extract_frames(self):
        if self._pil_full is None:
            return
        iw, ih = self._pil_full.size
        fw = iw // self._cols
        fh = ih // self._rows
        self._frames = []
        for r in range(self._rows):
            row_frames = []
            for c in range(self._cols):
                x0, y0 = c * fw, r * fh
                frame = self._pil_full.crop((x0, y0, x0 + fw, y0 + fh))
                row_frames.append(frame)
            self._frames.append(row_frames)

    def _apply_grid(self):
        try:
            new_cols = max(1, int(self._cols_var.get()))
            new_rows = max(1, int(self._rows_var.get()))
        except ValueError:
            return
        self._cols = new_cols
        self._rows = new_rows
        if self._pil_full:
            self._extract_frames()
            self._current_row   = min(self._current_row, self._rows - 1)
            self._current_frame = 0
            self._rebuild_row_buttons()
            self._update_thumb_strip()
            self._render_main()

    def _play(self):
        if not self._frames:
            return
        self._playing = True
        self._tick()

    def _stop(self):
        self._playing = False
        if self._anim_id:
            self.root.after_cancel(self._anim_id)
            self._anim_id = None

    def _toggle_play(self):
        if self._playing:
            self._stop()
        else:
            self._play()

    def _tick(self):
        if not self._playing:
            return
        self._current_frame = (self._current_frame + 1) % self._cols
        self._render_main()
        self._highlight_thumb(self._current_frame)
        self._anim_id = self.root.after(self._frame_ms, self._tick)

    def _step_frame(self):
        if not self._frames:
            return
        self._stop()
        self._current_frame = (self._current_frame + 1) % self._cols
        self._render_main()
        self._highlight_thumb(self._current_frame)

    def _select_row(self, row: int):
        if not self._frames:
            return
        self._current_row   = row
        self._current_frame = 0
        self._highlight_row_button()
        self._update_thumb_strip()
        self._render_main()

    def _on_speed_change(self, val):
        self._frame_ms = int(val)
        self._spd_label.config(text=f"{self._frame_ms}ms")

    def _render_main(self):
        if not self._frames:
            return
        self._canvas.delete("all")
        frame = self._frames[self._current_row][self._current_frame]
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        fw, fh = frame.size
        scale = min(cw / fw, ch / fh)
        dw, dh = max(1, int(fw * scale)), max(1, int(fh * scale))

        resized = frame.resize((dw, dh), Image.NEAREST)
        self._display_photo = ImageTk.PhotoImage(resized)
        self._canvas.create_image(cw // 2, ch // 2, anchor="center",
                                  image=self._display_photo)

        self._canvas.create_text(
            cw - 8, ch - 8,
            text=f"row {self._current_row}  frame {self._current_frame}",
            anchor="se", fill=FG_DIM, font=("Consolas", 8)
        )

    def _update_thumb_strip(self):
        self._thumb_canvas.delete("all")
        self._thumb_photos = []
        if not self._frames or self._current_row >= len(self._frames):
            return

        row_frames = self._frames[self._current_row]
        for i, frame in enumerate(row_frames):
            thumb = frame.resize((THUMB_SIZE, THUMB_SIZE), Image.NEAREST)
            photo = ImageTk.PhotoImage(thumb)
            self._thumb_photos.append(photo)

            x = i * (THUMB_SIZE + 8) + THUMB_SIZE // 2 + 4
            y = THUMB_SIZE // 2 + 8

            bg_color = BG_THUMB_HL if i == self._current_frame else BG_THUMB
            self._thumb_canvas.create_rectangle(
                x - THUMB_SIZE // 2 - 2, y - THUMB_SIZE // 2 - 2,
                x + THUMB_SIZE // 2 + 2, y + THUMB_SIZE // 2 + 2,
                fill=bg_color, outline=BORDER
            )
            self._thumb_canvas.create_image(x, y, anchor="center", image=photo)
            self._thumb_canvas.create_text(
                x, y + THUMB_SIZE // 2 + 10,
                text=str(i), fill=FG_DIM, font=("Consolas", 7)
            )
            idx = i
            tag = f"thumb_{i}"
            self._thumb_canvas.tag_bind(tag, "<Button-1>",
                                        lambda e, fi=idx: self._jump_to_frame(fi))
            self._thumb_canvas.addtag_withtag(tag, self._thumb_canvas.find_all()[-1])

        total_w = len(row_frames) * (THUMB_SIZE + 8) + 8
        self._thumb_canvas.config(scrollregion=(0, 0, total_w, THUMB_SIZE + 20))

    def _highlight_thumb(self, frame_idx: int):
        self._update_thumb_strip()

    def _jump_to_frame(self, frame_idx: int):
        self._stop()
        self._current_frame = frame_idx
        self._render_main()
        self._update_thumb_strip()

    def _show_empty_hint(self):
        self._canvas.delete("all")
        self.root.after(100, self._draw_hint)

    def _draw_hint(self):
        cw = self._canvas.winfo_width()  or 900
        ch = self._canvas.winfo_height() or 500
        cx, cy = cw // 2, ch // 2
        pad = 80
        self._canvas.create_rectangle(pad, pad, cw - pad, ch - pad,
                                      outline=BORDER, dash=(8, 6), fill="#0d0d1a")
        self._canvas.create_text(cx, cy - 20,
                                 text="Drop a sprite sheet here",
                                 fill="#3a5a7a", font=("Segoe UI", 16, "bold"))
        self._canvas.create_text(cx, cy + 14,
                                 text="or  Ctrl + O  /  Open button",
                                 fill=FG_DIM, font=("Segoe UI", 10))
        self._canvas.create_text(cx, cy + 38,
                                 text="Space: play/stop   →: step frame   ↑↓: change row",
                                 fill=FG_DIM, font=("Segoe UI", 9))

    def _set_status(self, text: str, error: bool = False):
        self._status.config(text=text, fg=FG_ERROR if error else FG_DIM)

    def _on_canvas_resize(self, event):
        if self._frames:
            self._render_main()
        else:
            self._draw_hint()


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.configure(bg=BG)
    app = SpriteViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
