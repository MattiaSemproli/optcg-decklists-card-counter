# ui_summary.py
# SummaryWindow: table with Avg, Occ, Total, ID, Name, Cost, Color, Power.

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import ttkbootstrap as tb
    TBOOT = tb
except Exception:
    TBOOT = None

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

        # Top: header + search
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

        # Table
        mid = ttk.Frame(master, padding=(10, 0, 10, 10))
        mid.pack(side="top", fill="both", expand=True)

        cols = ("Avg", "Occ", "Total", "ID", "Name", "Cost", "Color", "Power")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        self.tree.pack(side="left", fill="both", expand=True)

        style = ttk.Style()
        style.configure("Treeview", rowheight=24)
        self.tree.tag_configure("odd", background="#f7f7f7")
        self.tree.tag_configure("even", background="#ffffff")

        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c, False))

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

        # Bottom: actions
        bottom = ttk.Frame(master, padding=(10, 0, 10, 10))
        bottom.pack(side="bottom", fill="x")

        btn_copy = ttk.Button(bottom, text="Copy selection (Ctrl+C)", command=self._copy_selection)
        btn_copy.pack(side="left", padx=(0, 5))

        btn_csv = ttk.Button(bottom, text="Export CSV", command=self._export_csv)
        btn_csv.pack(side="left", padx=5)

        btn_txt = ttk.Button(bottom, text="Export TXT", command=self._export_txt)
        btn_txt.pack(side="left", padx=5)

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
        key_idx = {
            "Avg": 0, "Occ": 1, "Total": 2, "ID": 3,
            "Name": 4, "Cost": 5, "Color": 6, "Power": 7
        }[col]

        def key_func(row):
            val = row[key_idx]
            if key_idx in (0, 1, 2, 5, 7):  # numeric columns
                return -1 if val is None else val
            return str(val).lower()

        self.rows_view.sort(key=key_func, reverse=reverse)
        self._populate_table(self.rows_view)
        self.tree.heading(col, command=lambda c=col: self._sort_by_column(c, not reverse))

    def _on_search(self, event=None):
        q = (self.search_var.get() or "").strip().lower()
        if not q:
            self.rows_view = self.rows_all[:]
        else:
            def keep(r):
                return q in str(r[3]).lower() or q in str(r[4]).lower()
            self.rows_view = [r for r in self.rows_all if keep(r)]
        self._populate_table(self.rows_view)

    def _focus_search(self):
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
        import csv
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
