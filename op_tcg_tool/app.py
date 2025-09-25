# app.py
# App flow: InputWindow -> one SummaryWindow per leader. Hidden root, auto-exit on last close.

import tkinter as tk
try:
    import ttkbootstrap as tb
    TBOOT = tb
except Exception:
    TBOOT = None

from .core import decks_from_urls, group_decks_by_leader, summarize_decks, print_error
from .ui_summary import SummaryWindow

def launch_summary_windows(valid_links, root=None):
    """
    Build decks, group by leader, and open one summary window per leader group.
    If 'root' is provided, reuse it (expected already created by caller, typically the Input root).
    Otherwise, create a hidden root. App exits when the last summary window closes.
    """
    decks = decks_from_urls(valid_links)
    if not decks:
        print_error("No valid deck data could be parsed.")
        return

    groups, meta = group_decks_by_leader(decks)

    # Reuse caller root if provided, else create our own
    own_root = False
    if root is None:
        own_root = True
        if TBOOT:
            root = TBOOT.Window(themename="cosmo")
        else:
            root = tk.Tk()
        root.withdraw()  # keep hidden

    # Track open Toplevel windows
    root._open_windows = 0  # type: ignore[attr-defined]

    def make_on_close(win):
        def _on_close():
            try:
                win.destroy()
            except Exception:
                pass
            try:
                root._open_windows -= 1  # type: ignore[attr-defined]
            except Exception:
                pass
            if getattr(root, "_open_windows", 0) <= 0:
                # last window closed -> exit
                try:
                    root.quit()
                    root.destroy()
                except Exception:
                    pass
        return _on_close

    any_window = False
    for lid, decks_in_group in groups.items():
        rows, header_text, leader_name, colors = summarize_decks(decks_in_group)
        if not rows:
            continue

        # Create one Toplevel per leader group, parented to 'root'
        if TBOOT:
            win = TBOOT.Toplevel(root)
        else:
            win = tk.Toplevel(root)

        root._open_windows += 1  # type: ignore[attr-defined]
        win.protocol("WM_DELETE_WINDOW", make_on_close(win))

        title_suffix = leader_name or "Unknown Leader"
        SummaryWindow(win, rows, header_text, title_suffix=title_suffix)
        any_window = True

    if any_window:
        # If we created our own root, we need to run mainloop.
        # If we reuse caller root, it's already in mainloop.
        if own_root:
            root.mainloop()
    else:
        print_error("No rows to display after filtering (leaders are excluded).")
        try:
            if own_root:
                root.destroy()
        except Exception:
            pass
