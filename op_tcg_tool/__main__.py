# __main__.py
# Entry point: GUI-first; CLI fallback if Tk is not available.

from .core import parse_deckgen_url, print_error
import sys

# Tk availability check + UI imports here to avoid import errors in headless envs
try:
    import tkinter as tk
    from tkinter import ttk
    from .ui_input import InputWindow
    from .app import launch_summary_windows
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

def main():
    if TK_AVAILABLE:
        try:
            import ttkbootstrap as tb  # optional
            app = tb.Window(themename="cosmo")
        except Exception:
            import tkinter as tk
            app = tk.Tk()

        def _on_submit(valid_links):
            app.destroy()
            launch_summary_windows(valid_links)

        InputWindow(app, on_submit=_on_submit)
        app.mainloop()
        return

    # CLI fallback
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
        s = line.strip()
        if not s:
            break
        if not parse_deckgen_url(s):
            print_error("Invalid input: not a valid deckgen URL or missing 'dg' data.")
            continue
        urls.append(s)

    if not urls:
        print_error("No valid deckgen links provided. Exiting.")
        sys.exit(1)

    from .app import launch_summary_windows
    launch_summary_windows(urls)

if __name__ == "__main__":
    main()
