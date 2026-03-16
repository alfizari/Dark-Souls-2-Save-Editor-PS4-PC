import tkinter as tk
from tkinter import ttk, messagebox
import ds2 as BE 

BG       = "#0e0e0e"
BG2      = "#161616"
BG3      = "#1e1e1e"
PANEL    = "#121212"
BORDER   = "#2a2a2a"
GOLD     = "#c9a84c"
GOLD_DIM = "#7a6128"
EMBER    = "#cf4a1a"
RED      = "#8b1a1a"
ASH      = "#a0a0a0"
WHITE    = "#e8e2d4"
FONT_H   = ("Georgia", 14, "bold")
FONT_B   = ("Georgia", 10)
FONT_S   = ("Consolas", 9)

BTN_STYLE   = dict(bg=BG3, fg=GOLD, activebackground=BORDER, activeforeground=WHITE,
                   relief="flat", bd=0, padx=12, pady=5, font=FONT_B, cursor="hand2")
ENTRY_STYLE = dict(bg=BG2, fg=WHITE, insertbackground=GOLD, relief="flat", bd=1,
                   font=FONT_S, highlightbackground=BORDER, highlightcolor=GOLD,
                   highlightthickness=1)

# ── ttk styles ────────────────────────────────────────────────────────────────
def apply_ttk_styles():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("DS.TNotebook", background=BG, borderwidth=0, tabmargins=[2, 4, 2, 0])
    s.configure("DS.TNotebook.Tab", background=BG3, foreground=ASH,
                font=("Georgia", 10, "bold"), padding=[16, 8], borderwidth=0)
    s.map("DS.TNotebook.Tab",
          background=[("selected", PANEL)], foreground=[("selected", GOLD)])
    s.configure("DS.Treeview", background=BG2, foreground=WHITE,
                fieldbackground=BG2, font=FONT_S, rowheight=22, borderwidth=0)
    s.configure("DS.Treeview.Heading", background=BG3, foreground=GOLD,
                font=("Georgia", 9, "bold"), borderwidth=0)
    s.map("DS.Treeview",
          background=[("selected", GOLD_DIM)], foreground=[("selected", WHITE)])
    s.configure("DS.TCombobox", fieldbackground=BG2, background=BG3,
                foreground=WHITE, arrowcolor=GOLD, font=FONT_S)
    s.map("DS.TCombobox", fieldbackground=[("readonly", BG2)])

# ── widget helpers ────────────────────────────────────────────────────────────
def ghost_btn(parent, text, command=None, **kw):
    b = tk.Button(parent, text=text, command=command, **{**BTN_STYLE, **kw})
    b.bind("<Enter>", lambda e: b.config(bg=BORDER, fg=WHITE))
    b.bind("<Leave>", lambda e: b.config(bg=BG3, fg=GOLD))
    return b

def ember_btn(parent, text, command=None):
    b = tk.Button(parent, text=text, command=command,
                  bg=EMBER, fg=WHITE, activebackground="#a03010",
                  relief="flat", bd=0, padx=14, pady=6,
                  font=("Georgia", 10, "bold"), cursor="hand2")
    b.bind("<Enter>", lambda e: b.config(bg="#a03010"))
    b.bind("<Leave>", lambda e: b.config(bg=EMBER))
    return b

def section_label(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=GOLD,
             font=FONT_H, anchor="w").pack(fill="x", padx=16, pady=(12, 2))
    tk.Frame(parent, bg=GOLD, height=1).pack(fill="x", padx=16, pady=(0, 4))

def make_scrollable_frame(parent):
    outer  = tk.Frame(parent, bg=BG)
    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
    sb     = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=BG)
    win   = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(win, width=canvas.winfo_width())
    inner.bind("<Configure>", _on_inner)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
    canvas.bind_all("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
    return outer, inner


# ══════════════════════════════════════════════════════════════════════════════
#  SEARCHABLE TREEVIEW
# ══════════════════════════════════════════════════════════════════════════════
class SearchTree(tk.Frame):
    def __init__(self, parent, columns, qty_bar=False, on_qty=None, height=18, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._all_rows  = []
        self._columns   = [c[0] for c in columns]
        self._on_qty    = on_qty
        self._sort_col  = None
        self._sort_rev  = False

        if qty_bar:
            qbar = tk.Frame(self, bg=BG2, pady=6)
            qbar.pack(fill="x", padx=4, pady=(4, 0))
            tk.Label(qbar, text="Selected:", bg=BG2, fg=ASH, font=FONT_B).pack(side="left", padx=(8, 4))
            self._qty_name_var = tk.StringVar(value="—")
            tk.Label(qbar, textvariable=self._qty_name_var, bg=BG2, fg=WHITE,
                     font=("Consolas", 9), width=36, anchor="w").pack(side="left", padx=(0, 12))
            tk.Label(qbar, text="Qty:", bg=BG2, fg=ASH, font=FONT_B).pack(side="left")
            self._qty_var = tk.StringVar(value="")
            tk.Entry(qbar, textvariable=self._qty_var, width=7, **ENTRY_STYLE).pack(side="left", padx=6)
            ghost_btn(qbar, "Apply", command=self._apply_qty).pack(side="left", padx=4)
        else:
            self._qty_name_var = None
            self._qty_var      = None

        search_row = tk.Frame(self, bg=BG)
        search_row.pack(fill="x", padx=4, pady=(6, 2))
        tk.Label(search_row, text="🔍", bg=BG, fg=GOLD, font=FONT_B).pack(side="left")
        self._search_var = tk.StringVar()
        tk.Entry(search_row, textvariable=self._search_var, width=40, **ENTRY_STYLE).pack(side="left", padx=6)
        tk.Label(search_row, text="Filter items…", bg=BG, fg="#444",
                 font=("Consolas", 8, "italic")).pack(side="left")
        self._search_var.trace_add("write", lambda *_: self._filter())

        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree = ttk.Treeview(tree_frame, columns=self._columns,
                                 show="headings", style="DS.Treeview", height=height)
        for col_id, heading, width in columns:
            self.tree.heading(col_id, text=heading, command=lambda c=col_id: self._sort(c))
            self.tree.column(col_id, width=width, anchor="w")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        if qty_bar:
            self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def load(self, rows):
        self._all_rows = [(r, ()) for r in rows]
        self._filter()

    def _filter(self):
        query = self._search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        for values, _ in self._all_rows:
            if query and not any(query in str(v).lower() for v in values):
                continue
            self.tree.insert("", "end", values=values)

    def _sort(self, col):
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False
        idx = self._columns.index(col)
        self._all_rows.sort(key=lambda r: str(r[0][idx]).lower(), reverse=self._sort_rev)
        self._filter()

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return
        self._qty_name_var.set(vals[0])
        self._qty_var.set(str(vals[-1]) if len(vals) > 1 else "")

    def _apply_qty(self):
        name = self._qty_name_var.get() if self._qty_name_var else ""
        qty  = self._qty_var.get()      if self._qty_var      else ""
        if name == "—" or not name or not qty:
            return
        try:
            new_qty = int(qty)
        except ValueError:
            return
        if self._on_qty:
            self._on_qty(name, new_qty)

    def update_row_qty(self, item_name, new_qty):
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            if vals and vals[0] == item_name:
                vals[-1] = new_qty
                self.tree.item(iid, values=vals)
                break
        for i, (vals, tags) in enumerate(self._all_rows):
            if vals and vals[0] == item_name:
                lst     = list(vals)
                lst[-1] = new_qty
                self._all_rows[i] = (tuple(lst), tags)
                break


# ══════════════════════════════════════════════════════════════════════════════
#  ITEM NAME LOOKUP
# ══════════════════════════════════════════════════════════════════════════════
_REVERSE_MAP: dict = {}

def _build_reverse_map():
    global _REVERSE_MAP
    if not BE:
        return
    for d in [BE.goods_id, BE.rings_id, BE.weapons_id, BE.armors_id,
              BE.key_id, BE.bolts_id, BE.spells_id, BE.upgrade_id]:
        for name, hex_id in d.items():
            try:
                iid = int.from_bytes(bytes.fromhex(hex_id), "little")
                _REVERSE_MAP[iid] = name
            except Exception:
                continue

def _item_display_name(item_id_int):
    if not _REVERSE_MAP:
        _build_reverse_map()
    return _REVERSE_MAP.get(item_id_int, f"0x{item_id_int:08X}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
class DS2Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dark Souls II  ·  Save Editor")
        self.geometry("1150x780")
        self.minsize(900, 620)
        self.configure(bg=BG)
        _build_reverse_map()
        apply_ttk_styles()

        self.data           = None
        self.path           = None
        self._char_list     = []
        self._import_list   = []
        self._char_btn_map  = {}
        self._toast_after   = None

        self._build_header()
        self._build_notebook()
        self._build_statusbar()

    # ── header / status ───────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg="#090909", height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚔  DARK SOULS II  —  SAVE EDITOR",
                 bg="#090909", fg=GOLD,
                 font=("Georgia", 16, "bold")).pack(side="left", padx=20, pady=10)
        tk.Label(hdr, text="Mod at your own risk",
                 bg="#090909", fg="#999",
                 font=("Georgia", 9, "italic")).pack(side="left")
        tk.Label(hdr, text="      Made by Alfazari911",
                 bg="#090909", fg="#999",
                 font=("Georgia", 9, "italic")).pack(side="left")

    def _build_statusbar(self):
        self._status_var = tk.StringVar(value="No file loaded.")
        bar = tk.Frame(self, bg="#090909", height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Label(bar, textvariable=self._status_var, bg="#090909",
                 fg=ASH, font=("Consolas", 9), anchor="w").pack(side="left", padx=12)
        self._toast_var = tk.StringVar(value="")
        self._toast_lbl = tk.Label(bar, textvariable=self._toast_var,
                                   bg="#090909", fg="#4caf50",
                                   font=("Consolas", 9, "bold"), anchor="e")
        self._toast_lbl.pack(side="right", padx=16)

    def _status(self, msg):
        self._status_var.set(msg)

    def _toast(self, msg, duration_ms=2500):
        if self._toast_after:
            self.after_cancel(self._toast_after)
        self._toast_var.set(f"✓  {msg}")
        self._toast_after = self.after(duration_ms, lambda: self._toast_var.set(""))

    # ── notebook ──────────────────────────────────────────────────────────────
    def _build_notebook(self):
        self.nb = ttk.Notebook(self, style="DS.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        tabs = [
            ("  📂  File  ",        "_tab_file"),
            ("  🧙  Character  ",   "_tab_char"),
            ("  📊  Stats  ",       "_tab_stats"),
            ("  🎒  Inventory  ",   "_tab_inventory"),
            ("  ✨  Spawn Items  ", "_tab_spawn"),
        ]
        for label, attr in tabs:
            frame = tk.Frame(self.nb, bg=BG)
            setattr(self, attr, frame)
            self.nb.add(frame, text=label)

        self._build_file_tab()
        self._build_char_tab()
        self._build_stats_tab()
        self._build_inventory_tab()
        self._build_spawn_tab()

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 1 — FILE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_file_tab(self):
        outer, scroll = make_scrollable_frame(self._tab_file)
        outer.pack(fill="both", expand=True)

        section_label(scroll, "Open Save File")
        tk.Label(scroll,
                 text="Select a PS4 USERDATA file or PC DS2SOFS0000.sl2 file.\n"
                      "Characters found will appear as buttons below.",
                 bg=BG, fg=ASH, font=FONT_B, justify="left").pack(anchor="w", padx=24, pady=(0, 8))
        ghost_btn(scroll, "  Open File…", self._do_open).pack(anchor="w", padx=24, pady=4)

        section_label(scroll, "Characters Found")
        self._char_btns_frame = tk.Frame(scroll, bg=BG)
        self._char_btns_frame.pack(anchor="w", padx=24, pady=4)
        tk.Label(self._char_btns_frame, text="(open a file to see characters)",
                 bg=BG, fg="#444", font=("Consolas", 9)).pack()

        tk.Frame(scroll, bg=GOLD, height=1).pack(fill="x", padx=16, pady=12)

        section_label(scroll, "Save File")
        tk.Label(scroll, text="Write changes back to disk.",
                 bg=BG, fg=ASH, font=FONT_B).pack(anchor="w", padx=24, pady=(0, 8))
        ember_btn(scroll, "  💾  Save File", self._do_save).pack(anchor="w", padx=24, pady=4)

        tk.Frame(scroll, bg=GOLD, height=1).pack(fill="x", padx=16, pady=12)

        section_label(scroll, "Import Save (Character Import)")
        tk.Label(scroll,
                 text="Import a character from another save.\n"
                      "Load your main save first, select the destination character, "
                      "then click Import and choose the source character.\n"
                      "Importing will replace the current character's data.",
                 bg=BG, fg=ASH, font=FONT_B, justify="left").pack(anchor="w", padx=24, pady=(0, 8))
        ghost_btn(scroll, "  Open Import File…", self._do_open_import).pack(anchor="w", padx=24, pady=4)

        section_label(scroll, "Import — Characters Found")
        self._import_btns_frame = tk.Frame(scroll, bg=BG)
        self._import_btns_frame.pack(anchor="w", padx=24, pady=4)
        tk.Label(self._import_btns_frame, text="(open import file to see characters)",
                 bg=BG, fg="#444", font=("Consolas", 9)).pack()

    def _do_open(self):
        result = BE.open_file()
        if result is None:
            return
        char_list, source_path = result
        # DS2 open_file returns [(name, path), ...] for PC or (name, path) for PS4
        if isinstance(char_list, list):
            self._char_list = char_list
        else:
            self._char_list = [(char_list, source_path)]
        self._status(f"File scanned: {source_path}  —  {len(self._char_list)} character(s) found")
        self._refresh_char_buttons()

    def _refresh_char_buttons(self):
        for w in self._char_btns_frame.winfo_children():
            w.destroy()
        self._char_btn_map = {}   # index -> button
        if not self._char_list:
            tk.Label(self._char_btns_frame, text="(no characters found)",
                     bg=BG, fg="#444", font=("Consolas", 9)).pack()
            return
        for idx, (name, _) in enumerate(self._char_list):
            btn = ghost_btn(self._char_btns_frame, f"  👤  {name}",
                            command=lambda i=idx: self._load_character(i))
            btn.pack(side="left", padx=4)
            self._char_btn_map[idx] = btn

    def _load_character(self, idx):
        name, path = self._char_list[idx]
        with open(path, "rb") as f:
            self.data = f.read()
        self.path = path

        for i, btn in self._char_btn_map.items():
            if i == idx:
                btn.config(bg=RED, fg=WHITE)
                btn.unbind("<Enter>")
                btn.unbind("<Leave>")
            else:
                btn.config(bg=BG3, fg=GOLD)
                btn.bind("<Enter>", lambda e, b=btn: b.config(bg=BORDER, fg=WHITE))
                btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG3, fg=GOLD))

        self._status(f"Loaded: {name}  ({self.path})")
        self._toast(f"Character '{name}' loaded")
        self._refresh_all_tabs()

    def _do_save(self):
        if self.data is None:
            messagebox.showwarning("No File", "Load a character first.")
            return
        BE.save_file(self.path, self.data)
        self._toast("File saved successfully")

    def _do_open_import(self):
        result = BE.open_file_import()
        if result is None:
            return
        char_list, source_path = result
        self._import_list = char_list if isinstance(char_list, list) else [(char_list, source_path)]
        self._status(f"Import file scanned: {source_path}  —  {len(self._import_list)} character(s) found")
        self._refresh_import_buttons()

    def _refresh_import_buttons(self):
        for w in self._import_btns_frame.winfo_children():
            w.destroy()
        if not self._import_list:
            tk.Label(self._import_btns_frame, text="(no characters found)",
                     bg=BG, fg="#444", font=("Consolas", 9)).pack()
            return
        for idx, (name, _) in enumerate(self._import_list):
            ghost_btn(self._import_btns_frame, f"  👤  {name}",
                      command=lambda i=idx: self._do_import_character(i)
                      ).pack(side="left", padx=4)

    def _do_import_character(self, import_idx):
        if self.data is None:
            messagebox.showwarning("No File", "Load a destination character first.")
            return
        if self.path is None:
            messagebox.showwarning("No File", "No destination path set.")
            return

        import_char_name, import_path = self._import_list[import_idx]

        if not messagebox.askyesno(
            "Confirm Import",
            f"Import '{import_char_name}' into the current slot?\n"
            f"This will overwrite the loaded character's data."
        ):
            return

        new_data = BE.import_character(self.path, import_path)
        if new_data is None:
            return  # import_character already showed an error dialog

        self.data = new_data
        self._toast(f"Imported '{import_char_name}'")
        self._refresh_all_tabs()
        messagebox.showinfo("Import Successful",
                            f"Character '{import_char_name}' imported successfully.")

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 2 — CHARACTER
    # ══════════════════════════════════════════════════════════════════════════
    def _build_char_tab(self):
        p = self._tab_char
        self._char_vars = {}

        outer = tk.Frame(p, bg=BG)
        outer.pack(fill="both", expand=True, padx=32, pady=20)

        fields = [
            ("Character Name", "char_name", "str"),
            ("New Game Plus",  "ng",        "int"),
            ("Souls",          "souls",     "int"),
            ("HP",             "hp",        "int"),
        ]

        LABEL_W = 18
        ENTRY_W = 22

        for label, key, kind in fields:
            row = tk.Frame(outer, bg=BG)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=label, bg=BG, fg=ASH, font=FONT_B,
                     width=LABEL_W, anchor="w").pack(side="left")
            var = tk.StringVar(value="" if kind == "str" else "0")
            self._char_vars[key] = var
            tk.Entry(row, textvariable=var, width=ENTRY_W, **ENTRY_STYLE).pack(side="left", padx=8)
            ghost_btn(row, "Apply",
                      command=lambda k=key, t=kind: self._apply_char_field(k, t)
                      ).pack(side="left")

        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x", pady=14)

        btn_row = tk.Frame(outer, bg=BG)
        btn_row.pack(anchor="w")
        ember_btn(btn_row, "  Apply All", self._apply_all_char).pack(side="left", padx=(0, 10))
        ghost_btn(btn_row, "  Refresh",   self._refresh_char_tab).pack(side="left")

    def _apply_char_field(self, key, kind):
        if self.data is None:
            messagebox.showwarning("No File", "Load a character first.")
            return
        try:
            raw = self._char_vars[key].get()
            val = raw if kind == "str" else int(raw)
            data = bytearray(self.data)
            if   key == "char_name": data = BE.change_name(data, val)
            elif key == "souls":     data = BE.change_souls(data, val)
            elif key == "hp":        data = BE.change_hp(data, val)
            elif key == "ng":        data = BE.change_ng(data, val)
            self.data = bytes(data)
            self._toast(f"Applied: {key} = {val}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _apply_all_char(self):
        for key, kind in [("char_name", "str"), ("ng", "int"), ("souls", "int"), ("hp", "int")]:
            self._apply_char_field(key, kind)

    def _refresh_char_tab(self):
        if self.data is None:
            return
        try:
            info = BE.load_data(self.data)
            if not info:
                return
            self._char_vars["char_name"].set(info.get("name", ""))
            self._char_vars["ng"].set(str(info.get("ng", 0)))
            self._char_vars["souls"].set(str(info.get("souls", 0)))
            self._char_vars["hp"].set(str(info.get("hp", 0)))
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 3 — STATS
    # ══════════════════════════════════════════════════════════════════════════
    def _build_stats_tab(self):
        outer, scroll = make_scrollable_frame(self._tab_stats)
        outer.pack(fill="both", expand=True)

        section_label(scroll, "Character Statistics")
        self._stat_vars = {}

        stat_names = list(BE.stats_offsets_for_stats_tap.keys()) if BE else [
            "Level", "Vigor", "Attunement", "Endurance", "Vitality",
            "Strength", "Dexterity", "Intelligence", "Faith", "Adaptability",
        ]

        cols = tk.Frame(scroll, bg=BG)
        cols.pack(fill="both", expand=True, padx=16, pady=4)
        left  = tk.Frame(cols, bg=BG)
        right = tk.Frame(cols, bg=BG)
        left.pack(side="left",  fill="both", expand=True, padx=(8, 4))
        right.pack(side="left", fill="both", expand=True, padx=(4, 8))

        for i, stat in enumerate(stat_names):
            parent = left if i % 2 == 0 else right
            row = tk.Frame(parent, bg=BG)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=stat, bg=BG, fg=ASH, font=FONT_B,
                     width=28, anchor="w").pack(side="left")
            var = tk.StringVar(value="0")
            self._stat_vars[stat] = var
            tk.Entry(row, textvariable=var, width=8, **ENTRY_STYLE).pack(side="left", padx=4)

        tk.Frame(scroll, bg=GOLD, height=1).pack(fill="x", padx=16, pady=10)
        row = tk.Frame(scroll, bg=BG)
        row.pack(anchor="w", padx=24, pady=8)
        ember_btn(row, "  Apply All Stats", self._apply_all_stats).pack(side="left", padx=(0, 8))
        ghost_btn(row, "  Refresh",         self._refresh_stats_tab).pack(side="left")

    def _apply_all_stats(self):
        if self.data is None:
            messagebox.showwarning("No File", "Load a character first.")
            return
        data = bytearray(self.data)
        for stat, var in self._stat_vars.items():
            try:
                data = BE.change_stats(data, stat, int(var.get()))
            except Exception as e:
                messagebox.showerror("Error", f"{stat}: {e}")
                return
        self.data = bytes(data)
        self._toast("All stats applied")

    def _refresh_stats_tab(self):
        if self.data is None:
            return
        try:
            info = BE.load_data(self.data)
            if not info:
                return
            for stat, val in info.get("stats", {}).items():
                if stat in self._stat_vars:
                    self._stat_vars[stat].set(str(val))
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 4 — INVENTORY
    # ══════════════════════════════════════════════════════════════════════════
    def _build_inventory_tab(self):
        p = self._tab_inventory
        btn_row = tk.Frame(p, bg=BG)
        btn_row.pack(anchor="w", padx=24, pady=8)
        tk.Label(btn_row, text="Inventory", bg=BG, fg=GOLD, font=FONT_H).pack(side="left", padx=(0, 16))
        ghost_btn(btn_row, "  🔄 Refresh", self._refresh_inventory_tab).pack(side="left")

        # delete selected button
        ghost_btn(btn_row, "  🗑 Delete Selected",
                  self._delete_selected_item).pack(side="left", padx=(8, 0))

        inv_nb = ttk.Notebook(p, style="DS.TNotebook")
        inv_nb.pack(fill="both", expand=True, padx=8, pady=4)

        self._inv_trees = {}
        cats = [
            ("⚔ Weapons",  "weapons", False),
            ("🛡 Armors",   "armors",  False),
            ("🧪 Goods",    "goods",   True),
            ("💍 Rings",    "rings",   False),
            ("🔑 Keys",     "keys",    False),
            ("🏹 Bolts",    "bolts",   True),
            ("✨ Spells",   "spells",  False),
            ("🔧 Upgrade",  "upgrade", True),
        ]
        for label, key, has_qty in cats:
            frame = tk.Frame(inv_nb, bg=BG)
            inv_nb.add(frame, text=f"  {label}  ")
            if has_qty:
                cols = [("name", "Item Name", 340), ("id", "Item ID", 120), ("qty", "Qty", 60)]
                st = SearchTree(frame, columns=cols, qty_bar=True,
                                on_qty=lambda name, qty, k=key: self._inv_apply_qty(k, name, qty))
            else:
                cols = [("name", "Item Name", 340), ("id", "Item ID", 120)]
                st = SearchTree(frame, columns=cols)
            st.pack(fill="both", expand=True, padx=4, pady=4)
            self._inv_trees[key] = st

        self._inv_nb = inv_nb

    def _refresh_inventory_tab(self):
        if self.data is None:
            return
        try:
            inv = BE.inventoryprint(self.data)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        item_db = BE.build_item_db()

        def rows_nq(items):
            rows = []
            for item in items:
                name = item_db.get(item.item_id, (f"0x{item.item_id:08X}", ""))[0]
                rows.append((name, f"0x{item.item_id:08X}"))
            return rows

        def rows_q(items):
            rows = []
            for item in items:
                name = item_db.get(item.item_id, (f"0x{item.item_id:08X}", ""))[0]
                rows.append((name, f"0x{item.item_id:08X}", item.quantity))
            return rows

        self._inv_trees["weapons"].load(rows_nq(inv["weapons"]))
        self._inv_trees["armors"].load(rows_nq(inv["armors"]))
        self._inv_trees["goods"].load(rows_q(inv["goods"]))
        self._inv_trees["rings"].load(rows_nq(inv["rings"]))
        self._inv_trees["keys"].load(rows_nq(inv["keys"]))
        self._inv_trees["bolts"].load(rows_q(inv["bolts"]))
        self._inv_trees["spells"].load(rows_nq(inv["spells"]))
        self._inv_trees["upgrade"].load(rows_q(inv["upgrade"]))
        self._toast("Inventory refreshed")

    def _inv_apply_qty(self, category, item_name, new_qty):
        if self.data is None:
            return
        try:
            data = bytearray(self.data)
            data = BE.add_items(data, item_name, category, quantity=new_qty)
            self.data = bytes(data)
            self._inv_trees[category].update_row_qty(item_name, new_qty)
            self._toast(f"Inventory: {item_name} → {new_qty}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_selected_item(self):
        if self.data is None:
            messagebox.showwarning("No File", "Load a character first.")
            return
        # find which sub-tab is active
        cat_order = ["weapons", "armors", "goods", "rings", "keys", "bolts", "spells", "upgrade"]
        try:
            tab_idx = self._inv_nb.index(self._inv_nb.select())
        except Exception:
            return
        cat = cat_order[tab_idx]
        tree = self._inv_trees[cat]
        sel = tree.tree.selection()
        if not sel:
            messagebox.showwarning("Nothing Selected", "Select an item to delete.")
            return
        vals = tree.tree.item(sel[0], "values")
        if not vals:
            return
        item_name = vals[0]
        if not messagebox.askyesno("Confirm Delete", f"Delete '{item_name}' from inventory?"):
            return
        try:
            data = bytearray(self.data)
            data = BE.delete_item(data, item_name, cat)
            self.data = bytes(data)
            self._toast(f"Deleted: {item_name}")
            self._refresh_inventory_tab()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 5 — SPAWN ITEMS
    # ══════════════════════════════════════════════════════════════════════════
    def _build_spawn_tab(self):
        p = self._tab_spawn

        pane = tk.Frame(p, bg=BG)
        pane.pack(fill="both", expand=True)

        left = tk.Frame(pane, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(pane, bg="#0a0a0a", width=220)
        right.pack(side="right", fill="y", padx=(4, 6), pady=6)
        right.pack_propagate(False)

        tk.Label(right, text="▸ SPAWN LOG", bg="#0a0a0a", fg=GOLD,
                 font=("Consolas", 8, "bold"), anchor="w").pack(fill="x", padx=6, pady=(6, 2))
        tk.Frame(right, bg=GOLD, height=1).pack(fill="x", padx=6)

        self._spawn_log = tk.Text(right, bg="#0a0a0a", fg="#4caf50",
                                  font=("Consolas", 8), relief="flat", bd=0,
                                  state="disabled", wrap="word",
                                  highlightthickness=0, cursor="arrow")
        log_sb = ttk.Scrollbar(right, orient="vertical", command=self._spawn_log.yview)
        self._spawn_log.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y", pady=4)
        self._spawn_log.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        ghost_btn(right, "Clear", command=self._clear_spawn_log).pack(pady=(0, 4))

        spawn_nb = ttk.Notebook(left, style="DS.TNotebook")
        spawn_nb.pack(fill="both", expand=True, padx=8, pady=8)

        for label, builder in [
            ("  🧪 Goods  ",    self._build_spawn_goods),
            ("  ⚔ Weapons  ",   lambda f: self._build_spawn_single(f, "weapons")),
            ("  🛡 Armors  ",    lambda f: self._build_spawn_single(f, "armors")),
            ("  💍 Rings  ",     lambda f: self._build_spawn_single(f, "rings")),
            ("  🔑 Keys  ",      lambda f: self._build_spawn_single(f, "keys")),
            ("  🏹 Bolts  ",     lambda f: self._build_spawn_single(f, "bolts")),
            ("  ✨ Spells  ",    lambda f: self._build_spawn_single(f, "spells")),
            ("  🔧 Upgrade  ",   lambda f: self._build_spawn_single(f, "upgrade")),
        ]:
            frame = tk.Frame(spawn_nb, bg=BG)
            spawn_nb.add(frame, text=label)
            builder(frame)

    def _log_spawn(self, msg):
        import datetime
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self._spawn_log.config(state="normal")
        self._spawn_log.insert("end", line)
        self._spawn_log.see("end")
        self._spawn_log.config(state="disabled")

    def _clear_spawn_log(self):
        self._spawn_log.config(state="normal")
        self._spawn_log.delete("1.0", "end")
        self._spawn_log.config(state="disabled")

    def _build_spawn_goods(self, parent):
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", padx=16, pady=8)
        section_label(top, "Add Individual Good")

        row = tk.Frame(top, bg=BG)
        row.pack(anchor="w", padx=8, pady=4)
        self._spawn_goods_var = tk.StringVar()
        goods_names = list(BE.goods_id.keys()) if BE else []
        cb = self._make_search_combo(row, goods_names, self._spawn_goods_var, width=44)
        cb.pack(side="left", padx=(0, 8))
        tk.Label(row, text="Qty:", bg=BG, fg=ASH, font=FONT_B).pack(side="left")
        self._spawn_goods_qty = tk.StringVar(value="99")
        tk.Entry(row, textvariable=self._spawn_goods_qty, width=6, **ENTRY_STYLE).pack(side="left", padx=4)
        ghost_btn(row, "  Add", lambda: self._spawn_item(self._spawn_goods_var.get(), "goods",
                                                          self._safe_int(self._spawn_goods_qty.get(), 99))
                  ).pack(side="left", padx=8)

        tk.Frame(top, bg=GOLD, height=1).pack(fill="x", padx=8, pady=8)
        all_row = tk.Frame(top, bg=BG)
        all_row.pack(anchor="w", padx=8, pady=4)
        ember_btn(all_row, "  Bulk Add ALL Goods",
                  lambda: self._bulk_add("goods")).pack(side="left")
        #instructions for bulk add goods
        tk.Label(all_row, text="(adds 99 of each good), DO NOT BULK ADD EVERY SECTION (ex bulk adding weapons, goods, armors, rings at once. It will corrupt your save)" \
        ",\n Bulk add 1 tab then load the game and collect some items then try the others. Bulk adding everything will corrupt the game", bg=BG, fg=ASH, font=FONT_B).pack(side="left", padx=(8, 0))

    def _build_spawn_single(self, parent, category):
        label_map = {
            "weapons": "Weapon", "armors": "Armor", "rings": "Ring",
            "keys": "Key", "bolts": "Bolt", "spells": "Spell", "upgrade": "Upgrade Material",
        }
        label = label_map.get(category, category.title())
        section_label(parent, f"Add {label}")

        row = tk.Frame(parent, bg=BG)
        row.pack(anchor="w", padx=24, pady=8)

        src_map = {
            "weapons": BE.weapons_id, "armors": BE.armors_id, "rings": BE.rings_id,
            "keys": BE.key_id, "bolts": BE.bolts_id, "spells": BE.spells_id,
            "upgrade": BE.upgrade_id,
        }
        src = list(src_map.get(category, {}).keys()) if BE else []
        var = tk.StringVar()
        setattr(self, f"_spawn_{category}_var", var)
        cb = self._make_search_combo(row, src, var, width=52)
        cb.pack(side="left", padx=(0, 8))

        has_qty = category in ("bolts", "upgrade", "goods")
        qty_var = None
        if has_qty:
            tk.Label(row, text="Qty:", bg=BG, fg=ASH, font=FONT_B).pack(side="left")
            qty_var = tk.StringVar(value="99")
            tk.Entry(row, textvariable=qty_var, width=6, **ENTRY_STYLE).pack(side="left", padx=4)

        ghost_btn(row, "  Add",
                  command=lambda c=category, v=var, q=qty_var:
                      self._spawn_item(v.get(), c, self._safe_int(q.get(), 1) if q else 1)
                  ).pack(side="left")

        tk.Frame(parent, bg=GOLD, height=1).pack(fill="x", padx=16, pady=8)
        all_row = tk.Frame(parent, bg=BG)
        all_row.pack(anchor="w", padx=24, pady=4)
        ember_btn(all_row, f"  Bulk Add ALL {label}s",
                  lambda c=category: self._bulk_add(c)).pack(side="left")
        tk.Label(all_row, text=" DO NOT BULK ADD EVERY SECTION (ex bulk adding weapons, goods, armors, rings at once. It will corrupt your save)" \
        ",\n Bulk add 1 tab then load the game and collect some items then try the others. Bulk adding everything will corrupt the game", bg=BG, fg=ASH, font=FONT_B).pack(side="left", padx=(8, 0))


    def _spawn_item(self, name, category, qty=1):
        if self.data is None:
            messagebox.showwarning("No File", "Load a character first.")
            return
        if not name:
            return
        try:
            data = bytearray(self.data)
            data = BE.add_items(data, name, category, quantity=qty)
            self.data = bytes(data)
            self._toast(f"Added: {name} ×{qty}")
            self._log_spawn(f"+ {name} ×{qty}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _bulk_add(self, category):
        if self.data is None:
            messagebox.showwarning("No File", "Load a character first.")
            return
        if not messagebox.askyesno("Confirm", f"Bulk add ALL {category}?"):
            return
        src_map = {
            "goods": BE.goods_id, "weapons": BE.weapons_id, "armors": BE.armors_id,
            "rings": BE.rings_id, "keys": BE.key_id, "bolts": BE.bolts_id,
            "spells": BE.spells_id, "upgrade": BE.upgrade_id,
        }
        src = src_map.get(category, {})
        data = bytearray(self.data)
        count = 0
        for item_name in src:
            try:
                data = BE.add_items(data, item_name, category, quantity=99)
                count += 1
            except Exception:
                pass
        self.data = bytes(data)
        self._toast(f"Bulk added {count} {category}")
        self._log_spawn(f"★ Bulk all: {category} ({count} items)")

    # ── searchable combo ──────────────────────────────────────────────────────
    def _make_search_combo(self, parent, all_values, var, width=40):
        frame = tk.Frame(parent, bg=BG)
        entry = tk.Entry(frame, textvariable=var, width=width, **ENTRY_STYLE)
        entry.pack(side="left")

        _s = {"win": None, "lb": None, "_click_id": None}

        def _close():
            if _s["_click_id"]:
                try:
                    self.unbind("<Button-1>", _s["_click_id"])
                except Exception:
                    pass
                _s["_click_id"] = None
            if _s["win"] and _s["win"].winfo_exists():
                _s["win"].destroy()
            _s["win"] = None
            _s["lb"]  = None

        def _open(filtered):
            _close()
            if not filtered:
                return
            entry.update_idletasks()
            x = entry.winfo_rootx()
            y = entry.winfo_rooty() + entry.winfo_height() + 2
            w = max(entry.winfo_width(), 300)
            win = tk.Toplevel(self)
            win.overrideredirect(True)
            win.geometry(f"{w}x200+{x}+{y}")
            win.configure(bg=BG2)
            win.attributes("-topmost", True)
            _s["win"] = win
            lb_frame = tk.Frame(win, bg=BG2)
            lb_frame.pack(fill="both", expand=True)
            lb = tk.Listbox(lb_frame, bg=BG2, fg=WHITE,
                            selectbackground=GOLD_DIM, selectforeground=WHITE,
                            font=FONT_S, relief="flat", bd=0,
                            highlightthickness=0, activestyle="none")
            sb = ttk.Scrollbar(lb_frame, orient="vertical", command=lb.yview)
            lb.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            lb.pack(side="left", fill="both", expand=True)
            _s["lb"] = lb
            for v in filtered:
                lb.insert("end", v)

            def _pick(evt=None):
                sel = lb.curselection()
                if sel:
                    var.set(lb.get(sel[0]))
                _close()
                entry.focus_set()

            lb.bind("<ButtonRelease-1>", _pick)
            lb.bind("<Return>",          _pick)
            lb.bind("<Escape>",          lambda e: _close())

            def _on_global_click(evt):
                w_id = str(evt.widget)
                if str(entry) in w_id or (_s["win"] and str(_s["win"]) in w_id):
                    return
                _close()
            self.after(50, lambda: _s.update(
                {"_click_id": self.bind("<Button-1>", _on_global_click, add="+")}
            ))

        def _on_click(evt):
            q = var.get().lower()
            filtered = [v for v in all_values if q in v.lower()] if q else all_values
            _open(filtered)

        entry.bind("<Button-1>", _on_click)

        def _on_key(evt):
            if evt.keysym in ("Up", "Down", "Left", "Right",
                              "Shift_L", "Shift_R", "Control_L", "Control_R",
                              "Alt_L", "Alt_R", "Return", "Escape", "Tab", "Caps_Lock"):
                return
            q        = var.get().lower()
            filtered = [v for v in all_values if q in v.lower()] if q else all_values
            _open(filtered)

        def _on_arrow(evt):
            lb = _s["lb"]
            if lb is None:
                q        = var.get().lower()
                filtered = [v for v in all_values if q in v.lower()] if q else all_values
                _open(filtered)
                return
            cur = lb.curselection()
            nxt = (cur[0] + 1 if evt.keysym == "Down" else cur[0] - 1) if cur else (0 if evt.keysym == "Down" else lb.size() - 1)
            nxt = max(0, min(nxt, lb.size() - 1))
            lb.selection_clear(0, "end")
            lb.selection_set(nxt)
            lb.see(nxt)

        def _on_enter(evt):
            lb = _s["lb"]
            if lb:
                sel = lb.curselection()
                if sel:
                    var.set(lb.get(sel[0]))
                _close()

        entry.bind("<KeyRelease>", _on_key)
        entry.bind("<Down>",       _on_arrow)
        entry.bind("<Up>",         _on_arrow)
        entry.bind("<Return>",     _on_enter)
        entry.bind("<Escape>",     lambda e: _close())
        return frame

    # ══════════════════════════════════════════════════════════════════════════
    #  GLOBAL REFRESH
    # ══════════════════════════════════════════════════════════════════════════
    def _refresh_all_tabs(self):
        self._refresh_char_tab()
        self._refresh_stats_tab()
        self._refresh_inventory_tab()

    @staticmethod
    def _safe_int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = DS2Editor()
    app.mainloop()