# op_tcg_lists_average_counter.py
# NOTE: code and comments in ENGLISH (per your rule).
# GUI-first flow: input window -> summary table window.
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

def format_card_stats(card_info: dict) -> str:
    """
    Compact stat string for the table:
      - Events: [Event]
      - Otherwise prefer Power; then Generic cost; else '—'
    """
    if not card_info:
        return "—"
    cat = get_category(card_info)
    if cat == 'event':
        return "[Event]"
    power = card_info.get('Power')
    if power is not None and str(power).strip():
        return f"P{power}"
    cost = card_info.get('Cost')
    if isinstance(cost, dict) and cost.get('Generic') is not None:
        return f"C{cost.get('Generic')}"
    return "—"

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

def is_leader(card_info: dict) -> bool:
    return get_category(card_info) == 'leader'

def get_colors(card_info: dict):
    colors = (card_info or {}).get('Color')
    if isinstance(colors, list):
        return [str(c) for c in colors]
    if isinstance(colors, str) and colors.strip():
        return [colors.strip()]
    return []

def card_name(info: dict, fallback_id: str) -> str:
    """
    Always return something for the display name:
      try 'Name' -> 'Card Name' -> fallback to card ID.
    """
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

# --------------------------- aggregation ---------------------------
def summarize_decks(decks):
    """
    Aggregate stats across decks.
    Returns:
      rows: list of tuples (avg, occ, total, id, name, cost_val, stat, cat, crank)
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

    leader_name_val = None
    colors = []
    for d in decks:
        for cid in d:
            info = get_card(cid) or {}
            if is_leader(info):
                leader_name_val = card_name(info, cid)
                colors = get_colors(info)
                break
        if leader_name_val:
            break

    rows = []
    for cid in total_counts:
        info = get_card(cid) or {}
        nm = card_name(info, cid)
        stat = format_card_stats(info)
        cval = card_cost(info)  # numeric or None
        cat = get_category(info)
        crank = category_rank(cat)
        total = total_counts[cid]
        occ = occurrence[cid]
        avg_all = total / num_decks
        rows.append((avg_all, occ, total, cid, nm, cval, stat, cat, crank))

    # Default order: by category group, then by avg desc, then occ desc, then ID
    rows.sort(key=lambda r: (r[8], -r[0], -r[1], r[3]))

    header = f"Decks analyzed: {num_decks}"
    if colors:
        header += f" | Colors: {' / '.join(colors[:2])}"
    if leader_name_val:
        header += f" | Leader: {leader_name_val}"

    return rows, header, leader_name_val, colors

# --------------------------- GUI: summary window ---------------------------
class SummaryWindow:
    def __init__(self, master, rows, header_text):
        self.master = master
        self.rows_all = rows[:]   # (avg, occ, total, id, name, cost_val, stat, cat, crank)
        self.rows_view = rows[:]

        self._build_ui(header_text)
        self._populate_table(self.rows_view)

    def _build_ui(self, header_text: str):
        master = self.master
        master.title("OPTCG Decklists Summary")

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

        cols = ("Avg", "Occ", "Total", "ID", "Name", "Cost", "Stat")
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
        self.tree.column("Name", width=260, anchor="w")
        self.tree.column("Cost", width=70, anchor="e")
        self.tree.column("Stat", width=90, anchor="w")

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
        for idx, (avg, occ, total, cid, nm, cval, stat, _cat, _crank) in enumerate(rows):
            tag = "odd" if idx % 2 else "even"
            cost_disp = "—" if cval is None else str(cval)
            self.tree.insert("", "end",
                             values=(f"{avg:.2f}", occ, total, cid, nm, cost_disp, stat),
                             tags=(tag,))

    def _sort_by_column(self, col, reverse):
        # Map visible columns to row tuple indices
        key_idx = {"Avg": 0, "Occ": 1, "Total": 2, "ID": 3, "Name": 4, "Cost": 5, "Stat": 6}[col]

        def key_func(row):
            val = row[key_idx]
            # numeric columns: Avg, Occ, Total, Cost (index 0,1,2,5)
            if key_idx in (0, 1, 2, 5):
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
                # r = (avg, occ, total, id, name, cost_val, stat, cat, crank)
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
            w.writerow(["Avg", "Occ", "Total", "ID", "Name", "Cost", "Stat"])
            for r in self.rows_view:
                avg, occ, total, cid, nm, cval, stat, _cat, _crank = r
                w.writerow([f"{avg:.2f}", occ, total, cid, nm, "" if cval is None else cval, stat])
        messagebox.showinfo("Export CSV", f"Saved to:\n{path}")

    def _export_txt(self):
        path = self._ask_save_path(".txt", [("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        fmt = "{:>5}  {:>4}  {:>6}  {:<10}  {:<32}  {:>4}  {:<8}"
        lines = [fmt.format("Avg", "Occ", "Total", "ID", "Name", "Cost", "Stat"), "-" * 90]
        for avg, occ, total, cid, nm, cval, stat, _cat, _crank in self.rows_view:
            cost_disp = "" if cval is None else str(cval)
            lines.append(fmt.format(f"{avg:.2f}", str(occ), str(total), cid, nm[:32], cost_disp, stat))
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        messagebox.showinfo("Export TXT", f"Saved to:\n{path}")

# --------------------------- GUI: input window ---------------------------
class InputWindow:
    """
    First-step GUI: paste deckgen links (one per line), live-validate,
    and proceed to the summary table when at least one valid list exists.
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
        # Compare stripped content against invalid set
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
def _launch_summary_window(valid_links):
    decks = decks_from_urls(valid_links)
    rows, header_text, leader, colors = summarize_decks(decks)

    # Console snapshot (optional)
    print(header_text)
    fmt = "{:>5}  {:>4}  {:>6}  {:<10}  {:<32}  {:>4}  {:<8}"
    print(fmt.format("Avg", "Occ", "Total", "ID", "Name", "Cost", "Stat"))
    print("-" * 90)
    for avg, occ, total, cid, nm, cval, stat, _cat, _crank in rows:
        cost_disp = "" if cval is None else str(cval)
        print(fmt.format(f"{avg:.2f}", str(occ), str(total), cid, nm[:32], cost_disp, stat))

    # Open summary table UI
    if TK_AVAILABLE:
        if TBOOT:
            app = TBOOT.Window(themename="cosmo")
            SummaryWindow(app, rows, header_text)
            app.mainloop()
        else:
            root = tk.Tk()
            SummaryWindow(root, rows, header_text)
            root.mainloop()
    else:
        print_error("Tkinter is not available in this environment. GUI not shown.")

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
            # Close input window and move to summary
            # Create a NEW window for the summary to preserve theme/window state
            app.destroy()
            _launch_summary_window(valid_links)

        InputWindow(app, on_submit=_on_submit)
        app.mainloop()
        return

    # Fallback: CLI input
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

    _launch_summary_window(urls)

if __name__ == "__main__":
    main()
