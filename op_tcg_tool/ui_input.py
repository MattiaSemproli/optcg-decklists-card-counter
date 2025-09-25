# ui_input.py
# InputWindow: paste links, live-validate, Next enabled with ≥1 valid link.

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .core import parse_deckgen_url

try:
    import ttkbootstrap as tb
    TBOOT = tb
except Exception:
    TBOOT = None

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

        self.status_var.set(f"Valid: {len(self.valid_links)} · Invalid: {len(self.invalid_links)}")
        self._highlight_invalid(lines_all)
        self.next_btn.configure(state=("normal" if self.valid_links else "disabled"))

    def _highlight_invalid(self, lines_all):
        self.text.tag_remove("invalid", "1.0", "end")
        try:
            self.text.tag_configure("invalid", background="#ffe6e6")
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
