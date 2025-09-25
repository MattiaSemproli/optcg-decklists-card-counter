# op_tcg_lists_average_counter.py
# NOTE: code and comments in ENGLISH (per your rule).
# GUI-first flow: input window -> one summary window PER LEADER.
# CLI fallback remains if Tkinter isn't available.

import csv
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# --------------------------- optional terminal pretties ---------------------------
try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
    COLOR_RED = Fore.RED
    COLOR_RESET = Style.RESET_ALL
except Exception:
    COLOR_RED = "\033[31m"
    COLOR_RESET = "\033[0m"

# --------------------------- GUI (Tkinter / ttk / ttkbootstrap) -------------------
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

# Prefer ttkbootstrap for a nicer theme if present
TBOOT = None
if TK_AVAILABLE:
    try:
        import ttkbootstrap as tb
        TBOOT = tb
    except Exception:
        TBOOT = None

# --------------------------- optional cards DB accessor ---------------------------
try:
    from opc_sets import get_card
except Exception:
    def get_card(code: str):
        return None

# --------------------------- helpers ---------------------------
def print_error(msg: str) -> None:
    """Print a red error line without stopping the program."""
    print(f"{COLOR_RED}{msg}{COLOR_RESET}")

def get_category(info: dict) -> str:
    """Return normalized category string ('character', 'event', 'stage', 'leader', ...)."""
    if not info:
        return ""
    return (info.get('Category') or '').strip().lower()

def category_rank(cat: str) -> int:
    """
    Default grouping order:
      Character (0) < Event (1) < Stage (2) < others (3).
    """
    c = (cat or "").lower()
    if c == "character":
        return 0
    if c == "event":
        return 1
    if c == "stage":
        return 2
    return 3

def card_cost(info: dict):
    """
    Extract numeric Generic cost if available; otherwise return None.
    """
    if not info:
        return None
    cost = info.get('Cost')
    if isinstance(cost, dict):
        g = cost.get('Generic')
        if g is not None:
            try:
                return int(g)
            except Exception:
                try:
                    return int(float(g))
                except Exception:
                    return None
    elif isinstance(cost, (int, float, str)):
        try:
            return int(cost)
        except Exception:
            try:
                return int(float(cost))
            except Exception:
                return None
    return None

def card_power(info: dict):
    """Return numeric Power if present, else None."""
    if not info:
        return None
    p = info.get('Power')
    if p is None or str(p).strip() == "":
        return None
    try:
        return int(p)
    except Exception:
        try:
            return int(float(p))
        except Exception:
            return None

def card_colors(info: dict):
    """Return list of color strings."""
    colors = (info or {}).get('Color')
    if isinstance(colors, list):
        return [str(c) for c in colors]
    if isinstance(colors, str) and colors.strip():
        return [colors.strip()]
    return []

def card_color_str(info: dict) -> str:
    """Return display string for colors (joined with '/')."""
    cols = card_colors(info)
    return " / ".join(cols) if cols else ""

def is_leader(info: dict) -> bool:
    return get_category(info) == 'leader'

def card_name(info: dict, fallback_id: str) -> str:
    """Return Name -> Card Name -> card ID as fallback."""
    if not info:
        return fallback_id
    return (info.get("Name") or info.get("Card Name") or fallback_id)

# --------------------------- deckgen parsing ---------------------------
def parse_deckgen_url(url: str):
    """
    Parse a onepiecetopdecks deckgen URL and return a list of (card_id, count).
    Uses the 'dg' query param which encodes like: 1nOP03-040a4nOP03-044...
    Return [] if invalid or no 'dg'.
    """
    try:
        qs = parse_qs(urlparse(url).query)
        dg = qs.get("dg", [""])[0]
        if not dg:
            return []
        parts = dg.split("a")
        out = []
        for part in parts:
            if not part or "n" not in part:
                continue
            cnt_str, code = part.split("n", 1)
            cnt_str = cnt_str.strip()
            code = code.strip()
            if not cnt_str.isdigit() or not code:
                return []  # treat the whole line as invalid
            out.append((code, int(cnt_str)))
        return out
    except Exception:
        return []

def decks_from_urls(urls):
    """Return a list of deck dicts: [{card_id: count, ...}, ...]."""
    decks = []
    for u in urls:
        pairs = parse_deckgen_url(u)
        if not pairs:
            continue
        deck = defaultdict(int)
        for cid, n in pairs:
            deck[cid] += n
        decks.append(dict(deck))
    return decks

# --------------------------- leader inference & grouping ---------------------------
def infer_deck_leader(deck: dict):
    """
    Given a single deck {card_id: count}, return (leader_id, leader_name, leader_colors_list) if any;
    otherwise (None, None, []).
    """
    for cid in deck:
        info = get_card(cid) or {}
        if is_leader(info):
            return cid, card_name(info, cid), card_colors(info)
    return None, None, []

def group_decks_by_leader(decks):
    """
    Partition decks by inferred leader ID.
    Returns:
      groups: dict[leader_id_or_None] -> list[deck]
      meta: dict[leader_id_or_None] -> {"name": str|None, "colors": list[str]}
    Decks with no detectable leader are grouped under key None.
    """
    groups = defaultdict(list)
    meta = {}
    for d in decks:
        lid, lname, lcols = infer_deck_leader(d)
        groups[lid].append(d)
        if lid not in meta:
            meta[lid] = {"name": lname, "colors": lcols}
    return groups, meta

# --------------------------- aggregation ---------------------------
def summarize_decks(decks):
    """
    Aggregate stats across decks (leaders are EXCLUDED from the rows).
    Returns:
      rows: list of tuples (avg, occ, total, id, name, cost_val, color_str, power_val, cat, crank)
      header_text: str
      leader_name_val: str|None
      colors: list[str]
    """
    if not decks:
        return [], "No valid lists found.", None, []

    num_decks = len(decks)
    total_counts = Counter()
    occurrence = Counter()
    for d in decks:
        total_counts.update(d)
        for cid in d:
            occurrence[cid] += 1

    # detect a leader just for header (may be None)
    leader_name_val = None
    colors = []
    lid, lname, lcols = infer_deck_leader(decks[0]) if decks else (None, None, [])
    leader_name_val = lname
    colors = lcols

    rows = []
    for cid in total_counts:
        info = get_card(cid) or {}
        cat = get_category(info)
        if cat == "leader":
            continue  # EXCLUDE leaders from rows

        nm = card_name(info, cid)
        cval = card_cost(info)          # numeric or None
        pval = card_power(info)         # numeric or None
        colstr = card_color_str(info)   # "Red", "Blue / Green", ...
        crank = category_rank(cat)
        total = total_counts[cid]
        occ = occurrence[cid]
        avg_all = total / num_decks
        rows.append((avg_all, occ, total, cid, nm, cval, colstr, pval, cat, crank))

    # Default order: by category group, then by avg desc, then occ desc, then ID
    rows.sort(key=lambda r: (r[9], -r[0], -r[1], r[3]))

    header = f"Decks analyzed: {num_decks}"
    if colors:
        header += f" | Colors: {' / '.join(colors[:2])}"
    if leader_name_val:
        header += f" | Leader: {leader_name_val}"

    return rows, header, leader_name_val, colors

# --------------------------- GUI: summary window ---------------------------
class SummaryWindow:
    def __init__(self, master, rows, header_text, title_suffix: str = ""):
        self.master = master
        self.rows_all = rows[:]   # (avg, occ, total, id, name, cost_val, color_str, power_val, cat, crank)
        self.rows_view = rows[:]

        self._build_ui(header_text, title_suffix)
        self._populate_table(self.rows_view)

    def _build_ui(self, header_text: str, title_suffix: str):
        master = self.master
        base_title = "OPTCG Decklists Summary"
        if title_suffix:
            base_title += f" — {title_suffix}"
        master.title(base_title)

        if TBOOT:
            TBOOT.Style("cosmo")
        else:
            ttk.Style(master)

        # Top frame: header + search
        top = ttk.Frame(master, padding=10)
        top.pack(side="top", fill="x")

        self.header_var = tk.StringVar(value=header_text)
        ttk.Label(top, textvariable=self.header_var, font=("Segoe UI", 10, "bold")).pack(side="left")

        search_frame = ttk.Frame(top)
        search_frame.pack(side="right")
        ttk.Label(search_frame, text="Search: ").pack(side="left")
        self.search_var = tk.StringVar()
        ent = ttk.Entry(search_frame, textvariable=self.search_var, width=28)
        ent.pack(side="left")
        ent.bind("<KeyRelease>", self._on_search)

        # Middle frame: table
        mid = ttk.Frame(master, padding=(10, 0, 10, 10))
        mid.pack(side="top", fill="both", expand=True)

        cols = ("Avg", "Occ", "Total", "ID", "Name", "Cost", "Color", "Power")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        self.tree.pack(side="left", fill="both", expand=True)

        # Zebra striping
        style = ttk.Style()
        style.configure("Treeview", rowheight=24)
        self.tree.tag_configure("odd", background="#f7f7f7")
        self.tree.tag_configure("even", background="#ffffff")

        # Headings with sort commands
        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c, False))

        # Column widths
        self.tree.column("Avg", width=70, anchor="e")
        self.tree.column("Occ", width=60, anchor="e")
        self.tree.column("Total", width=70, anchor="e")
        self.tree.column("ID", width=100, anchor="w")
        self.tree.column("Name", width=240, anchor="w")
        self.tree.column("Cost", width=60, anchor="e")
        self.tree.column("Color", width=120, anchor="w")
        self.tree.column("Power", width=70, anchor="e")

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        # Bottom frame: actions
        bottom = ttk.Frame(master, padding=(10, 0, 10, 10))
        bottom.pack(side="bottom", fill="x")

        btn_copy = ttk.Button(bottom, text="Copy selection (Ctrl+C)", command=self._copy_selection)
        btn_copy.pack(side="left", padx=(0, 5))

        btn_csv = ttk.Button(bottom, text="Export CSV", command=self._export_csv)
        btn_csv.pack(side="left", padx=5)

        btn_txt = ttk.Button(bottom, text="Export TXT", command=self._export_txt)
        btn_txt.pack(side="left", padx=5)

        # Shortcuts
        master.bind_all("<Control-f>", lambda e: self._focus_search())
        master.bind_all("<Control-F>", lambda e: self._focus_search())
        master.bind_all("<Control-c>", lambda e: self._copy_selection())
        master.bind_all("<Control-C>", lambda e: self._copy_selection())

    def _populate_table(self, rows):
        self.tree.delete(*self.tree.get_children())
        for idx, (avg, occ, total, cid, nm, cval, colstr, pval, _cat, _crank) in enumerate(rows):
            tag = "odd" if idx % 2 else "even"
            cost_disp = "" if cval is None else str(cval)
            pow_disp = "" if pval is None else str(pval)
            self.tree.insert("", "end",
                             values=(f"{avg:.2f}", occ, total, cid, nm, cost_disp, colstr, pow_disp),
                             tags=(tag,))

    def _sort_by_column(self, col, reverse):
        # Map visible columns to row tuple indices
        key_idx = {
            "Avg": 0, "Occ": 1, "Total": 2, "ID": 3,
            "Name": 4, "Cost": 5, "Color": 6, "Power": 7
        }[col]

        def key_func(row):
            val = row[key_idx]
            # numeric columns: Avg, Occ, Total, Cost, Power
            if key_idx in (0, 1, 2, 5, 7):
                return -1 if val is None else val
            return str(val).lower()

        self.rows_view.sort(key=key_func, reverse=reverse)
        self._populate_table(self.rows_view)
        # toggle for next click
        self.tree.heading(col, command=lambda c=col: self._sort_by_column(c, not reverse))

    def _on_search(self, event=None):
        q = (self.search_var.get() or "").strip().lower()
        if not q:
            self.rows_view = self.rows_all[:]
        else:
            def keep(r):
                # r = (avg, occ, total, id, name, cost_val, color_str, power_val, cat, crank)
                return q in str(r[3]).lower() or q in str(r[4]).lower()
            self.rows_view = [r for r in self.rows_all if keep(r)]
        self._populate_table(self.rows_view)

    def _focus_search(self):
        # Focus the search entry
        for w in self.master.winfo_children():
            for ww in w.winfo_children():
                if isinstance(ww, (ttk.Entry,)):
                    ww.focus_set()
                    ww.select_range(0, 'end')
                    return

    def _copy_selection(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Copy", "No rows selected.")
            return
        rows_txt = []
        for iid in sel:
            vals = self.tree.item(iid, "values")
            rows_txt.append("\t".join(str(v) for v in vals))
        txt = "\n".join(rows_txt)
        self.master.clipboard_clear()
        self.master.clipboard_append(txt)
        messagebox.showinfo("Copy", f"Copied {len(sel)} row(s) to clipboard.")

    def _ask_save_path(self, default_ext, filetypes, default_name_prefix="summary"):
        dt_string = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{default_name_prefix}_{dt_string}{default_ext}"
        return filedialog.asksaveasfilename(defaultextension=default_ext,
                                            filetypes=filetypes,
                                            initialfile=default_name)

    def _export_csv(self):
        path = self._ask_save_path(".csv", [("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Avg", "Occ", "Total", "ID", "Name", "Cost", "Color", "Power"])
            for r in self.rows_view:
                avg, occ, total, cid, nm, cval, colstr, pval, _cat, _crank = r
                w.writerow([f"{avg:.2f}", occ, total, cid, nm,
                            "" if cval is None else cval,
                            colstr,
                            "" if pval is None else pval])
        messagebox.showinfo("Export CSV", f"Saved to:\n{path}")

    def _export_txt(self):
        path = self._ask_save_path(".txt", [("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        fmt = "{:>5}  {:>4}  {:>6}  {:<10}  {:<28}  {:>4}  {:<12}  {:>5}"
        lines = [fmt.format("Avg", "Occ", "Total", "ID", "Name", "Cost", "Color", "Power"), "-" * 100]
        for avg, occ, total, cid, nm, cval, colstr, pval, _cat, _crank in self.rows_view:
            cost_disp = "" if cval is None else str(cval)
            pow_disp = "" if pval is None else str(pval)
            lines.append(fmt.format(f"{avg:.2f}", str(occ), str(total), cid, nm[:28], cost_disp, colstr[:12], pow_disp))
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        messagebox.showinfo("Export TXT", f"Saved to:\n{path}")

# --------------------------- GUI: input window ---------------------------
class InputWindow:
    """
    First-step GUI: paste deckgen links (one per line), live-validate,
    and proceed to one or more summary windows (one per leader).
    """
    def __init__(self, master, on_submit):
        # on_submit: callable(list[str]) -> None
        self.master = master
        self.on_submit = on_submit
        self.valid_links = []
        self.invalid_links = []

        self._build_ui()

    def _build_ui(self):
        self.master.title("OPTCG Decklists - Input")

        container = ttk.Frame(self.master, padding=10)
        container.pack(fill="both", expand=True)

        header = ttk.Label(container, text="Paste deckgen links (one per line)", font=("Segoe UI", 11, "bold"))
        header.pack(anchor="w", pady=(0, 6))

        # Buttons row
        btn_row = ttk.Frame(container)
        btn_row.pack(fill="x", pady=(0, 6))
        ttk.Button(btn_row, text="Paste from clipboard", command=self._paste_clipboard).pack(side="left")
        ttk.Button(btn_row, text="Load .txt…", command=self._load_txt).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Clear", command=self._clear).pack(side="left")

        # Text area
        self.text = tk.Text(container, height=12, wrap="none", font=("Consolas", 10))
        self.text.pack(fill="both", expand=True)
        self.text.bind("<KeyRelease>", self._on_text_change)
        self.text.bind("<Control-Return>", self._on_ctrl_enter)

        # Status + Next
        bottom = ttk.Frame(container)
        bottom.pack(fill="x", pady=(6, 0))

        self.status_var = tk.StringVar(value="Valid: 0 · Invalid: 0")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="left")

        self.next_btn = ttk.Button(bottom, text="Next →", command=self._submit, state="disabled")
        self.next_btn.pack(side="right")

        # Initial validation
        self._validate()

    def _paste_clipboard(self):
        try:
            clip = self.master.clipboard_get() or ""
        except Exception:
            clip = ""
        if not clip:
            return
        lines = clip.strip().splitlines()
        self._insert_lines(lines)

    def _load_txt(self):
        path = filedialog.askopenfilename(
            title="Open links list",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception:
            messagebox.showerror("Open error", "Failed to read the file.")
            return
        lines = content.splitlines()
        self._insert_lines(lines)

    def _clear(self):
        self.text.delete("1.0", "end")
        self._validate()

    def _insert_lines(self, lines):
        # Deduplicate while keeping order
        seen = set()
        deduped = []
        for ln in lines:
            ln = ln.strip()
            if ln and ln not in seen:
                seen.add(ln)
                deduped.append(ln)
        if deduped:
            current = self.text.get("1.0", "end-1c")
            if current:
                self.text.insert("end", "\n" + "\n".join(deduped))
            else:
                self.text.insert("1.0", "\n".join(deduped))
        self._validate()

    def _on_text_change(self, event=None):
        self._validate()

    def _on_ctrl_enter(self, event=None):
        self._submit()
        return "break"

    def _validate(self):
        content = self.text.get("1.0", "end-1c")
        lines_all = content.splitlines()

        # Build lists based on stripped non-empty lines
        self.valid_links = []
        self.invalid_links = []

        for ln in lines_all:
            s = ln.strip()
            if not s:
                continue
            pairs = parse_deckgen_url(s)
            if pairs:
                self.valid_links.append(s)
            else:
                self.invalid_links.append(s)

        # Update status
        self.status_var.set(f"Valid: {len(self.valid_links)} · Invalid: {len(self.invalid_links)}")

        # Highlight invalid lines in the text widget
        self._highlight_invalid(lines_all)

        # Enable Next only if we have at least one valid link
        self.next_btn.configure(state=("normal" if self.valid_links else "disabled"))

    def _highlight_invalid(self, lines_all):
        self.text.tag_remove("invalid", "1.0", "end")
        try:
            self.text.tag_configure("invalid", background="#ffe6e6")  # light red
        except Exception:
            pass
        invalid_set = set(self.invalid_links)
        for i, raw in enumerate(lines_all):
            s = raw.strip()
            if s and s in invalid_set:
                line_start = f"{i+1}.0"
                line_end = f"{i+1}.end"
                self.text.tag_add("invalid", line_start, line_end)

    def _submit(self):
        if not self.valid_links:
            messagebox.showwarning("No lists", "Please add at least one valid deckgen link.")
            return
        self.on_submit(self.valid_links)

# --------------------------- flow helpers ---------------------------
def _launch_summary_windows(valid_links):
    """
    Build decks, group them by leader, and open one summary window per leader group.
    Root window stays hidden; app exits automatically when the last summary window closes.
    """
    decks = decks_from_urls(valid_links)
    if not decks:
        print_error("No valid deck data could be parsed.")
        return

    groups, meta = group_decks_by_leader(decks)

    if not TK_AVAILABLE:
        print_error("Tkinter is not available in this environment. GUI not shown.")
        return

    # Create a single hidden root
    if TBOOT:
        root = TBOOT.Window(themename="cosmo")
    else:
        root = tk.Tk()
    root.withdraw()  # keep root hidden, no "mini window"

    # Track how many top-level windows are open; when the last one closes, exit the app
    root._open_windows = 0  # type: ignore[attr-defined]

    def make_on_close(win):
        def _on_close():
            try:
                win.destroy()
            except Exception:
                pass
            # decrement counter and quit app if no windows remain
            try:
                root._open_windows -= 1  # type: ignore[attr-defined]
            except Exception:
                pass
            if getattr(root, "_open_windows", 0) <= 0:
                try:
                    root.quit()
                    root.destroy()
                except Exception:
                    pass
        return _on_close

    any_window = False
    for lid, decks_in_group in groups.items():
        rows, header_text, leader_name, colors = summarize_decks(decks_in_group)

        # Console snapshot (optional)
        print(header_text)
        fmt = "{:>5}  {:>4}  {:>6}  {:<10}  {:<28}  {:>4}  {:<12}  {:>5}"
        print(fmt.format("Avg", "Occ", "Total", "ID", "Name", "Cost", "Color", "Power"))
        print("-" * 100)
        for avg, occ, total, cid, nm, cval, colstr, pval, _cat, _crank in rows:
            cost_disp = "" if cval is None else str(cval)
            pow_disp = "" if pval is None else str(pval)
            print(fmt.format(f"{avg:.2f}", str(occ), str(total), cid, nm[:28], cost_disp, colstr[:12], pow_disp))

        if not rows:
            continue

        # Create one Toplevel per leader group
        if TBOOT:
            win = TBOOT.Toplevel(root)
        else:
            win = tk.Toplevel(root)

        # Increment window counter and attach close handler
        root._open_windows += 1  # type: ignore[attr-defined]
        win.protocol("WM_DELETE_WINDOW", make_on_close(win))

        title_suffix = leader_name or "Unknown Leader"
        SummaryWindow(win, rows, header_text, title_suffix=title_suffix)
        any_window = True

    if any_window:
        # No deiconify(): root stays hidden; mainloop runs until last Toplevel is closed
        root.mainloop()
    else:
        print_error("No rows to display after filtering (leaders are excluded).")
        try:
            root.destroy()
        except Exception:
            pass

# --------------------------- main ---------------------------
def main():
    # If Tkinter is available, prefer GUI-first flow.
    if TK_AVAILABLE:
        # Choose themed window if ttkbootstrap is available
        if TBOOT:
            app = TBOOT.Window(themename="cosmo")
        else:
            app = tk.Tk()

        def _on_submit(valid_links):
            # Close input window and move to multiple summary windows (one per leader)
            app.destroy()
            _launch_summary_windows(valid_links)

        InputWindow(app, on_submit=_on_submit)
        app.mainloop()
        return

    # Fallback: CLI input (single-pass, still groups by leader when rendering)
    print("Paste one deckgen link per line.")
    print("Press ENTER on an empty line to finish.\n")

    urls = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if not line:
            break
        line = line.strip()
        if not line:
            break

        pairs = parse_deckgen_url(line)
        if not pairs:
            print_error("Invalid input: not a valid deckgen URL or missing 'dg' data.")
            continue
        urls.append(line)

    if not urls:
        print_error("No valid deckgen links provided. Exiting.")
        return

    _launch_summary_windows(urls)

if __name__ == "__main__":
    main()
