# utils.py
# Shared utility functions for window management, formatting, etc.

def center_window(win, rel_width=0.8, rel_height=0.8):
    """
    Resize and center a Tkinter window on the screen.
    rel_width and rel_height are relative fractions of the screen size.
    """
    win.update_idletasks()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()

    w = int(screen_w * rel_width)
    h = int(screen_h * rel_height)
    x = (screen_w // 2) - (w // 2)
    y = (screen_h // 2) - (h // 2)

    win.geometry(f"{w}x{h}+{x}+{y}")
