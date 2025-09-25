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

def format_card_stats(card_info: dict) -> str:
    """
    Compact stat string for the table:
    - Events: [Event]
    - Otherwise, prefer Power; then Generic cost; else '—'
    """
    if not card_info:
        return "—"
    category = (card_info.get('Category') or '').strip().lower()
    if category == 'event':
        return "[Event]"
    power = card_info.get('Power')
    if power is not None and str(power).strip():
        return f"P{power}"
    cost = card_info.get('Cost')
    if isinstance(cost, dict) and cost.get('Generic') is not None:
        return f"C{cost.get('Generic')}"
    return "—"

def is_leader(card_info: dict) -> bool:
    return bool(card_info) and (card_info.get('Category') or '').strip().lower() == 'leader'

def get_colors(card_info: dict):
    colors = (card_info or {}).get('Color')
    if isinstance(colors, list):
        return [str(c) for c in colors]
    if isinstance(colors, str) and colors.strip():
        return [colors.strip()]
    return []

def card_name(info: dict, fallback_id: str) -> str:
    """Always return a name: 'Name' -> 'Card Name' -> card ID."""
    if not info:
        return fallback_id
    return (info.get("Name") or info.get("Card Name") or fallback_id)

# --------------------------- deckgen parsing ---------------------------
def parse_deckgen_url(url: str):
    """
    Parse a onepiecetopdecks deckgen URL and return a list of (card_id, count).
    Uses the 'dg' query param which encodes like: 1nOP03-040a4nOP03-044...
    Return [] if invalid.
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
            # protected by validation in input loop; keep guard
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
      rows: list of tuples (avg, occ, total, id, name, stat)
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
        total = total_counts[cid]
        occ = occurrence[cid]
        avg_all = total / num_decks
        rows.append((avg_all, occ, total, cid, nm, stat))

    rows.sort(key=lambda x: (-x[0], -x[1], x[3]))

    header = f"Decks analyzed: {num_decks}"
    if colors:
        header += f" | Colors: {' / '.join(colors[:2])}"
    if leader_name_val:
        header += f" | Leader: {leader_name_val}"

    return rows, header, leader_name_val, colors

# --------------------------- GUI window ---------------------------
class SummaryWindow:
    def __init__(self, master, rows, header_text):
        self.master = master
        self.rows_all = rows[:]   # full dataset
        self.rows_view = rows[:]  # filtered/sorted view

        self._build_ui(header_text)
        self._populate_table(self.rows_view)

    def _build_ui(self, header_text: str):
        master = self.master
        master.title("OPTCG Decklists Summary")

        # Use ttkbootstrap theme if available
        if TBOOT:
            style = TBOOT.Style("cosmo")  # or "flatly", "darkly", etc.
        else:
            style = ttk.Style(master)

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

        cols = ("Avg", "Occ", "Total", "ID", "Name", "Stat")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        self.tree.pack(side="left", fill="both", expand=True)

        # Zebra striping
        style.configure("Treeview", rowheight=24)
        self.tree.tag_configure("odd", background="#f7f7f7")
        self.tree.tag_configure("even", background="#ffffff")

        # Headings with sort commands
        for i, col in enumerate(cols):
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c, False))

        # Column widths
        self.tree.column("Avg", width=70, anchor="e")
        self.tree.column("Occ", width=60, anchor="e")
        self.tree.column("Total", width=70, anchor="e")
        self.tree.column("ID", width=100, anchor="w")
        self.tree.column("Name", width=260, anchor="w")
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
        for idx, (avg, occ, total, cid, nm, stat) in enumerate(rows):
            tag = "odd" if idx % 2 else "even"
            self.tree.insert("", "end", values=(f"{avg:.2f}", occ, total, cid, nm, stat), tags=(tag,))

    def _sort_by_column(self, col, reverse):
        key_idx = {"Avg": 0, "Occ": 1, "Total": 2, "ID": 3, "Name": 4, "Stat": 5}[col]

        def key_func(row):
            val = row[key_idx]
            if key_idx in (0, 1, 2):  # numeric
                return row[key_idx]
            return str(val).lower()

        self.rows_view.sort(key=key_func, reverse=reverse)
        self._populate_table(self.rows_view)
        # toggle next
        self.tree.heading(col, command=lambda c=col: self._sort_by_column(c, not reverse))

    def _on_search(self, event=None):
        q = (self.search_var.get() or "").strip().lower()
        if not q:
            self.rows_view = self.rows_all[:]
        else:
            def keep(r):
                # r = (avg, occ, total, id, name, stat)
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
            w.writerow(["Avg", "Occ", "Total", "ID", "Name", "Stat"])
            for r in self.rows_view:
                avg, occ, total, cid, nm, stat = r
                w.writerow([f"{avg:.2f}", occ, total, cid, nm, stat])
        messagebox.showinfo("Export CSV", f"Saved to:\n{path}")

    def _export_txt(self):
        path = self._ask_save_path(".txt", [("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        fmt = "{:>5}  {:>4}  {:>6}  {:<10}  {:<32}  {:<8}"
        lines = [fmt.format("Avg", "Occ", "Total", "ID", "Name", "Stat"), "-" * 80]
        for avg, occ, total, cid, nm, stat in self.rows_view:
            lines.append(fmt.format(f"{avg:.2f}", str(occ), str(total), cid, nm[:32], stat))
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        messagebox.showinfo("Export TXT", f"Saved to:\n{path}")

# --------------------------- main ---------------------------
def main():
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

    decks = decks_from_urls(urls)
    rows, header_text, leader, colors = summarize_decks(decks)

    # Console snapshot (useful for logs)
    print(header_text)
    fmt = "{:>5}  {:>4}  {:>6}  {:<10}  {:<32}  {:<8}"
    print(fmt.format("Avg", "Occ", "Total", "ID", "Name", "Stat"))
    print("-" * 80)
    for avg, occ, total, cid, nm, stat in rows:
        print(fmt.format(f"{avg:.2f}", str(occ), str(total), cid, nm[:32], stat))

    # Launch GUI if Tkinter is available
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

if __name__ == "__main__":
    main()
