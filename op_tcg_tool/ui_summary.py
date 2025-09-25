# ui_summary.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
from pathlib import Path
from datetime import datetime

from .utils import center_window, center_child

# Optional: matplotlib for histogram popups
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPL_OK = True
except Exception:
    MPL_OK = False


class SummaryWindow:
    """
    Summary table UI for one leader group.
    Shows columns: Avg, Occ, Total, ID, Name, Cost, Stat.
    - Clicking the 'Occ' cell opens a popup with per-deck counts (e.g., 3x, 2x).
    - 'Histogram' button opens a popup with histograms of Cost, Type, Counter
      (weights by total copies).
    """
    def __init__(self, master, rows, header_text, title_suffix=None,
                 perdeck_counts=None, total_counts=None):
        self.master = master
        self.rows_all = rows[:]   # (avg, occ, total, id, name, cost_val, stat, cat, crank)
        self.rows_view = rows[:]
        self.perdeck_counts = perdeck_counts or {}
        self.total_counts = total_counts or {}

        # Size & center
        center_window(self.master, 0.8, 0.8)

        # Title
        base_title = "OPTCG Decklists Summary"
        if title_suffix:
            self.master.title(f"{base_title} — {title_suffix}")
        else:
            self.master.title(base_title)

        self._build_ui(header_text)
        self._populate_table(self.rows_view)

    # ---------------- UI build ----------------
    def _build_ui(self, header_text: str):
        master = self.master

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

        # Middle: table
        mid = ttk.Frame(master, padding=(10, 0, 10, 10))
        mid.pack(side="top", fill="both", expand=True)

        cols = ("Avg", "Occ", "Total", "ID", "Name", "Cost", "Stat")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        self.tree.pack(side="left", fill="both", expand=True)

        # Zebra
        style = ttk.Style()
        style.configure("Treeview", rowheight=24)
        self.tree.tag_configure("odd", background="#f7f7f7")
        self.tree.tag_configure("even", background="#ffffff")

        # Headings with sort
        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c, False))

        # Column widths / anchors
        self.tree.column("Avg", width=70, anchor="e")
        self.tree.column("Occ", width=60, anchor="e")
        self.tree.column("Total", width=70, anchor="e")
        self.tree.column("ID", width=110, anchor="w")
        self.tree.column("Name", width=300, anchor="w")
        self.tree.column("Cost", width=70, anchor="e")
        self.tree.column("Stat", width=100, anchor="w")

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        # Bind click to detect Occ cell
        self.tree.bind("<Button-1>", self._on_tree_click)

        # Bottom: actions
        bottom = ttk.Frame(master, padding=(10, 0, 10, 10))
        bottom.pack(side="bottom", fill="x")

        btn_copy = ttk.Button(bottom, text="Copy selection (Ctrl+C)", command=self._copy_selection)
        btn_copy.pack(side="left", padx=(0, 5))

        btn_csv = ttk.Button(bottom, text="Export CSV", command=self._export_csv)
        btn_csv.pack(side="left", padx=5)

        btn_txt = ttk.Button(bottom, text="Export TXT", command=self._export_txt)
        btn_txt.pack(side="left", padx=5)

        # NEW: Histogram button
        btn_hist = ttk.Button(bottom, text="Histogram", command=self._open_histogram_popup,
                              state=("normal" if MPL_OK else "disabled"))
        btn_hist.pack(side="left", padx=5)

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

    # ---------------- Sorting & Search ----------------
    def _sort_by_column(self, col, reverse):
        key_idx = {"Avg": 0, "Occ": 1, "Total": 2, "ID": 3, "Name": 4, "Cost": 5, "Stat": 6}[col]

        def key_func(row):
            val = row[key_idx]
            if key_idx in (0, 1, 2, 5):
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

    # ---------------- Tree click: Occ popup ----------------
    def _on_tree_click(self, event):
        # identify which column/row was clicked
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col_id = self.tree.identify_column(event.x)  # '#1'..'#N'
        row_id = self.tree.identify_row(event.y)
        if not row_id or col_id != "#2":  # '#2' is Occ
            return

        vals = self.tree.item(row_id, "values")
        if not vals:
            return
        card_id = vals[3]  # ID column

        counts = self.perdeck_counts.get(card_id, [])
        occ = len(counts)
        msg_lines = [f"Card '{card_id}' present in {occ} deck(s)."]
        if counts:
            sorted_counts = sorted(counts, reverse=True)
            msg_lines.append("Counts by deck: " + ", ".join(f"{c}x" for c in sorted_counts))

        # popup
        pop = tk.Toplevel(self.master)
        pop.title("Occurrence details")
        lab = ttk.Label(pop, text="\n".join(msg_lines), padding=12, justify="left")
        lab.pack(fill="both", expand=True)
        ttk.Button(pop, text="Close", command=pop.destroy).pack(pady=8)
        center_child(self.master, pop, 0.4, 0.25)

    def _open_histogram_popup(self):
        if not MPL_OK:
            messagebox.showwarning("Histogram", "matplotlib is not available in this environment.")
            return

        from collections import Counter as Cntr
        cost_counter = Cntr()
        type_counter = Cntr()
        counter_counter = Cntr()

        from op_tcg_tool.core import get_card  # safe import here

        for cid, total in self.total_counts.items():
            info = get_card(cid) or {}
            # cost
            cost = None
            cdict = info.get("Cost")
            if isinstance(cdict, dict) and ("Generic" in cdict):
                try:
                    cost = int(cdict.get("Generic"))
                except Exception:
                    pass
            elif isinstance(cdict, (int, float, str)):
                try:
                    cost = int(float(cdict))
                except Exception:
                    pass
            if cost is not None:
                cost_counter[cost] += int(total)

            # types
            types = info.get("Type") or []
            if isinstance(types, list):
                for t in types:
                    type_counter[str(t)] += int(total)

            # counter value
            ctr = info.get("Counter")
            if isinstance(ctr, (int, float, str)):
                try:
                    cv = int(float(ctr))
                    counter_counter[cv] += int(total)
                except Exception:
                    pass

        pop = tk.Toplevel(self.master)
        pop.title("Histograms")
        nb = ttk.Notebook(pop)
        nb.pack(fill="both", expand=True)

        # Keep references to resize handlers (avoid GC)
        self._mpl_tabs = []

        def make_bar_tab(parent, title, labels, values, xlabel):
            frame = ttk.Frame(parent)
            frame.pack_propagate(False)  # we handle sizing ourselves
            parent.add(frame, text=title)

            # Create figure a bit arbitrary; we'll resize it immediately on <Configure>
            fig = Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)
            ax.bar(labels, values)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Total copies")
            ax.grid(axis='y', linestyle=':', alpha=0.5)
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.pack(fill="both", expand=True)

            # Resize figure to match frame size dynamically
            def on_conf(event):
                # event.width/height are the inner size of the frame
                w = max(event.width, 100)
                h = max(event.height, 100)
                dpi = fig.get_dpi()
                fig.set_size_inches(w / dpi, h / dpi, forward=True)
                fig.tight_layout()
                canvas.draw_idle()

            frame.bind("<Configure>", on_conf)

            # store so we can refresh on tab change
            self._mpl_tabs.append((frame, fig, canvas, on_conf))
            
        # ---- NEW: horizontal bars helper (for long labels) ----
        def make_barh_tab(parent, title, labels, values, ylabel, max_label_chars=28):
            import textwrap
            # shorten labels (opzionale; evita etichette interminabili)
            def shorten(s):
                s = str(s)
                if len(s) <= max_label_chars:
                    return s
                return textwrap.shorten(s, width=max_label_chars, placeholder="…")

            labels_sh = [shorten(l) for l in labels]

            frame = ttk.Frame(parent)
            frame.pack_propagate(False)
            parent.add(frame, text=title)

            fig = Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)
            ax.barh(labels_sh, values)
            ax.set_ylabel(ylabel)
            ax.set_xlabel("Total copies")
            ax.grid(axis='x', linestyle=':', alpha=0.5)

            # lascia spazio a sinistra per le etichette
            fig.subplots_adjust(left=0.28, right=0.98, top=0.95, bottom=0.10)

            # ordinare con la barra più grande in alto (più leggibile)
            ax.invert_yaxis()

            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.pack(fill="both", expand=True)

            # resize dinamico
            def on_conf(event):
                w = max(event.width, 100)
                h = max(event.height, 100)
                dpi = fig.get_dpi()
                fig.set_size_inches(w / dpi, h / dpi, forward=True)
                fig.tight_layout(rect=(0.22, 0.08, 0.98, 0.98))
                canvas.draw_idle()

            frame.bind("<Configure>", on_conf)
            self._mpl_tabs.append((frame, fig, canvas, on_conf))


        # Cost tab
        if cost_counter:
            costs_sorted = sorted(cost_counter.items())
            labels = [str(k) for k, _ in costs_sorted]
            values = [v for _, v in costs_sorted]
            make_bar_tab(nb, "Cost", labels, values, "Cost")

        # Type tab (use horizontal bars to avoid label overlap)
        if type_counter:
            # sort desc by count
            types_sorted = sorted(type_counter.items(), key=lambda kv: (-kv[1], kv[0]))

            # (opzionale) limita a Top-N e raggruppa il resto in "Others"
            TOP_N = 20
            if len(types_sorted) > TOP_N:
                head = types_sorted[:TOP_N]
                tail_sum = sum(v for _, v in types_sorted[TOP_N:])
                head.append(("Others", tail_sum))
                types_sorted = head

            labels = [k for k, _ in types_sorted]
            values = [v for _, v in types_sorted]

            # usa la tab orizzontale
            make_barh_tab(nb, "Type", labels, values, "Type")


        # Counter tab
        if counter_counter:
            ctr_sorted = sorted(counter_counter.items())
            labels = [str(k) for k, _ in ctr_sorted]
            values = [v for _, v in ctr_sorted]
            make_bar_tab(nb, "Counter", labels, values, "Counter")

            # When switching tabs, force a refresh of the active canvas to the tab's current size
            def on_tab_changed(event=None):
                sel = nb.select()
                if not sel:
                    return
                for (frame, fig, canvas, _handler) in self._mpl_tabs:
                    if str(frame) == str(sel):
                        w = max(frame.winfo_width(), 100)
                        h = max(frame.winfo_height(), 100)
                        dpi = fig.get_dpi()
                        fig.set_size_inches(w / dpi, h / dpi, forward=True)
                        fig.tight_layout()
                        canvas.draw_idle()
                        break

            nb.bind("<<NotebookTabChanged>>", on_tab_changed)

            # Center the popup relative to the parent
            center_child(self.master, pop, 0.7, 0.6)

            # --- NEW: force a first proper layout for the initially selected tab ---
            pop.update_idletasks()         # ensure sizes are computed
            on_tab_changed()               # trigger the same logic used on tab change

            # As an extra safeguard, run it once more after the window is fully shown
            pop.after(50, on_tab_changed)

    # ---------------- Copy / Export ----------------
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
