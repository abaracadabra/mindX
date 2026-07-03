#!/usr/bin/env python3
# GNUGUI — the public-facing client for GNUVAULT (and for BANKON).
# Copyright (C) 2026 cypherpunk2048 / BANKON.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.  Distributed WITHOUT ANY WARRANTY.  See <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GNUGUI — both brand new and antiquated. A pseudo-3D, cypherpunk2048 GUI over a
GNUVAULT Mausoleum: each tomb is drawn as an isometric vault block; you can
inter (seal), exhume (open), and — the part that matters — **export the key**,
which is the sovereign exit.

This is a *prototype* in the resurrected Tomb-suite lineage (gtomb → GNUGUI),
written in pure-stdlib Tkinter so it runs anywhere Python does, no CDN, no web.
**BANKON will use GNUGUI in its public-facing client software**; this is that
client's open, auditable core. take it, own it, use it, share it.

Headless-safe: if there is no display, it prints the slogans and exits 0 rather
than crashing — so it is importable and testable in CI.

    python3 gnugui.py            # opens the window (needs a display)
    python3 gnugui.py --headless # prints status, draws nothing
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Import the suite from the same folder (standalone-friendly).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mausoleum import Mausoleum, SLOGANS  # noqa: E402
from gnuvault import CYPHERPUNK2048_STANDARD  # noqa: E402

# cypherpunk2048 palette (matches artist.agent / the standard).
GROUND = "#0a0a12"
GOLD = "#d4af37"
GREEN = "#36966e"
INK = "#e4e4ec"
MUTED = "#9698a8"


def _has_display() -> bool:
    if os.environ.get("DISPLAY") or sys.platform == "darwin" or os.name == "nt":
        try:
            import tkinter  # noqa: F401
            return True
        except Exception:
            return False
    return False


def _iso(x: int, y: int, z: int = 0) -> tuple[int, int]:
    """Trivial isometric projection (the 'pseudo-3D')."""
    return (x - y), ((x + y) // 2 - z)


class GnuGui:
    def __init__(self, mausoleum: Mausoleum) -> None:
        import tkinter as tk
        self.tk = tk
        self.m = mausoleum
        self.root = tk.Tk()
        self.root.title("GNUGUI — GNUVAULT mausoleum (cypherpunk2048)")
        self.root.configure(bg=GROUND)
        self.root.geometry("1024x768")  # the cypherpunk2048 4:3 poster size

        self.canvas = tk.Canvas(self.root, width=720, height=768, bg=GROUND, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        side = tk.Frame(self.root, bg=GROUND, width=300)
        side.pack(side="right", fill="y")
        tk.Label(side, text="GNUGUI", fg=GOLD, bg=GROUND,
                 font=("DejaVu Sans", 28, "bold")).pack(pady=(18, 0))
        tk.Label(side, text="the mausoleum holds your tombs", fg=MUTED, bg=GROUND,
                 font=("DejaVu Sans", 11)).pack()
        self.listbox = tk.Listbox(side, bg="#101220", fg=INK, selectbackground=GREEN,
                                  highlightthickness=0, bd=0, font=("DejaVu Sans Mono", 11))
        self.listbox.pack(fill="x", padx=16, pady=12)
        for label, cmd in [("＋ inter (new tomb)", self._inter), ("🔓 exhume (open)", self._exhume),
                           ("🔁 rekey", self._rekey), ("🔑 export key → sovereign", self._export),
                           ("💾 backup → …", self._backup), ("📥 import tomb", self._import),
                           ("🗑 forget", self._forget), ("↻ refresh", self._refresh)]:
            tk.Button(side, text=label, command=cmd, bg=GOLD, fg=GROUND, bd=0,
                      activebackground=GREEN, font=("DejaVu Sans", 11, "bold")).pack(
                          fill="x", padx=16, pady=2)
        tk.Label(side, text=SLOGANS[2], fg=GOLD, bg=GROUND, wraplength=270,
                 font=("DejaVu Sans", 10, "italic")).pack(side="bottom", pady=10)
        self._refresh()

    def _refresh(self) -> None:
        self.listbox.delete(0, "end")
        tombs = self.m.list_tombs()
        for t in tombs:
            self.listbox.insert("end", f"  ⚰ {t.name}")
        self._draw(tombs)

    def _draw(self, tombs) -> None:
        c = self.canvas
        c.delete("all")
        cx, cy = 360, 200
        # ground grid
        for i in range(-6, 7):
            x0, y0 = _iso(i * 40, -240); x1, y1 = _iso(i * 40, 240)
            c.create_line(cx + x0, cy + y0, cx + x1, cy + y1, fill="#1a1c2a")
            x0, y0 = _iso(-240, i * 40); x1, y1 = _iso(240, i * 40)
            c.create_line(cx + x0, cy + y0, cx + x1, cy + y1, fill="#1a1c2a")
        # one isometric vault block per tomb
        for idx, t in enumerate(tombs or []):
            gx = (idx % 4) * 90 - 135
            gy = (idx // 4) * 90 - 45
            self._block(cx + _iso(gx, gy)[0], cy + _iso(gx, gy)[1], t.name)
        c.create_text(360, 720, fill=MUTED, font=("DejaVu Sans", 12),
                      text="cypherpunk2048 · " + CYPHERPUNK2048_STANDARD)
        c.create_text(360, 740, fill=GOLD, font=("DejaVu Sans", 11, "italic"),
                      text=SLOGANS[3])

    def _block(self, x: int, y: int, name: str) -> None:
        c = self.canvas
        s = 36
        # top face (gold), left + right faces (darker) — the 3D illusion
        c.create_polygon(x, y - s, x + s, y - s // 2, x, y, x - s, y - s // 2,
                         fill=GOLD, outline=GREEN)
        c.create_polygon(x - s, y - s // 2, x, y, x, y + s, x - s, y + s // 2,
                         fill="#7a6322", outline=GREEN)
        c.create_polygon(x + s, y - s // 2, x, y, x, y + s, x + s, y + s // 2,
                         fill="#5a4a1a", outline=GREEN)
        c.create_text(x, y + s + 12, fill=INK, font=("DejaVu Sans", 10), text=name)

    def _prompt(self, title: str, secret: bool = False):
        from tkinter import simpledialog
        return simpledialog.askstring(title, title, show="*" if secret else None, parent=self.root)

    def _selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self.m.list_tombs()[sel[0]].name

    def _inter(self) -> None:
        from tkinter import messagebox
        name = self._prompt("tomb name")
        if not name:
            return
        secret = self._prompt("secret to seal", secret=True)
        pw = self._prompt("passphrase", secret=True)
        if secret is None or not pw:
            return
        try:
            self.m.inter(name, secret, pw)
            self._refresh()
        except Exception as e:
            messagebox.showerror("inter failed", str(e))

    def _exhume(self) -> None:
        from tkinter import messagebox
        name = self._selected()
        if not name:
            return
        pw = self._prompt(f"passphrase for {name}", secret=True)
        if not pw:
            return
        try:
            messagebox.showinfo(name, self.m.exhume(name, pw).decode("utf-8", "replace"))
        except Exception:
            messagebox.showerror("exhume failed", "wrong passphrase (failed closed)")

    def _export(self) -> None:
        from tkinter import messagebox
        name = self._selected()
        if not name:
            return
        pw = self._prompt(f"passphrase for {name}", secret=True)
        if not pw:
            return
        try:
            key = self.m.export_key(name, pw, fmt="hex")
            messagebox.showinfo(f"{name} — key is now sovereign",
                                f"{key}\n\nThe key has left the running system. "
                                "Hold it, or build your own.")
        except Exception:
            messagebox.showerror("export failed", "wrong passphrase (failed closed)")

    def _rekey(self) -> None:
        from tkinter import messagebox
        name = self._selected()
        if not name:
            return
        old = self._prompt(f"current passphrase for {name}", secret=True)
        new = self._prompt("new passphrase", secret=True)
        if not old or not new:
            return
        try:
            self.m.rekey(name, old, new)
            messagebox.showinfo(name, "rekeyed — passphrase rotated in place")
        except Exception:
            messagebox.showerror("rekey failed", "wrong current passphrase (failed closed)")

    def _backup(self) -> None:
        from tkinter import messagebox, filedialog
        dest = filedialog.askdirectory(parent=self.root, title="Back up tombs to… (e.g. a USB mount)")
        if not dest:
            return
        try:
            written = self.m.backup(dest, verify=True)
            messagebox.showinfo("backup", f"backed up {len(written)} tomb(s), sha256-verified →\n{dest}")
        except Exception as e:
            messagebox.showerror("backup failed", str(e))

    def _import(self) -> None:
        from tkinter import messagebox, filedialog
        path = filedialog.askopenfilename(parent=self.root, title="Import a tomb (*.tomb.json)",
                                          filetypes=[("GNUVAULT tomb", "*.tomb.json"), ("All", "*")])
        if not path:
            return
        try:
            info = self.m.import_tomb(path)
            self._refresh()
            messagebox.showinfo("import", f"imported ⚰ {info.name}")
        except Exception as e:
            messagebox.showerror("import failed", str(e))

    def _forget(self) -> None:
        from tkinter import messagebox
        name = self._selected()
        if not name:
            return
        if not messagebox.askyesno("forget", f"Remove tomb ⚰ {name} from the mausoleum?\n"
                                   "(external copies/backups are not shredded)"):
            return
        self.m.forget(name)
        self._refresh()

    def run(self) -> None:
        self.root.mainloop()


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    headless = "--headless" in argv or not _has_display()
    m = Mausoleum()
    if headless:
        print("GNUGUI (headless) — GNUVAULT mausoleum client.")
        print(f"  tombs: {len(m.list_tombs())} at {m.root}")
        print(f"  standard: {CYPHERPUNK2048_STANDARD}")
        for s in SLOGANS:
            print(f"  · {s}")
        return 0
    GnuGui(m).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
