# utils.py
# Shared utility functions for window management.

def center_window(win, rel_width=0.8, rel_height=0.8):
    """
    Resize and center a Tkinter window on the screen.
    rel_width and rel_height are fractions of the screen size (0..1).
    """
    win.update_idletasks()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()

    w = int(screen_w * rel_width)
    h = int(screen_h * rel_height)
    x = (screen_w // 2) - (w // 2)
    y = (screen_h // 2) - (h // 2)

    win.geometry(f"{w}x{h}+{x}+{y}")


def _apply_geometry(win, x, y, w, h):
    """Set exact pixel geometry to a window."""
    win.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")


def tile_summary_windows(root, windows):
    """
    Arrange summary windows depending on count:
      1 -> 80% x 80% centered
      2 -> each 40% width x 80% height, side-by-side
      3 -> each 30% width x 80% height, in one row
      4 -> each 40% width x 40% height, 2x2 grid

    If count is different, falls back to a simple grid with up to 3 columns.
    """
    if not windows:
        return

    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    n = len(windows)

    if n == 1:
        center_window(windows[0], 0.8, 0.8)
        return

    rects = []

    if n == 2:
        w = int(screen_w * 0.40)
        h = int(screen_h * 0.80)
        gap_x = (screen_w - 2 * w) // 3  # symmetric margins
        x1 = gap_x
        x2 = gap_x * 2 + w
        y = (screen_h - h) // 2
        rects = [(x1, y, w, h), (x2, y, w, h)]

    elif n == 3:
        w = int(screen_w * 0.30)
        h = int(screen_h * 0.80)
        gap_x = (screen_w - 3 * w) // 4
        y = (screen_h - h) // 2
        x1 = gap_x
        x2 = gap_x * 2 + w
        x3 = gap_x * 3 + w * 2
        rects = [(x1, y, w, h), (x2, y, w, h), (x3, y, w, h)]

    elif n == 4:
        w = int(screen_w * 0.40)
        h = int(screen_h * 0.40)
        gap_x = (screen_w - 2 * w) // 3
        gap_y = (screen_h - 2 * h) // 3
        x1 = gap_x
        x2 = gap_x * 2 + w
        y1 = gap_y
        y2 = gap_y * 2 + h
        rects = [
            (x1, y1, w, h), (x2, y1, w, h),
            (x1, y2, w, h), (x2, y2, w, h),
        ]

    else:
        # Fallback: grid with up to 3 columns, 80% height rows
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        w = int(screen_w * (0.90 / cols))   # leave some margins
        h = int(screen_h * (0.85 / rows))
        total_w = w * cols
        total_h = h * rows
        start_x = (screen_w - total_w) // 2
        start_y = (screen_h - total_h) // 2
        rects = []
        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx >= n:
                    break
                x = start_x + c * w
                y = start_y + r * h
                rects.append((x, y, w, h))
                idx += 1

    for win, (x, y, w, h) in zip(windows, rects):
        _apply_geometry(win, x, y, w, h)

# utils.py (ADD)

def center_child(parent, child, rel_width=0.6, rel_height=0.6):
    """
    Size the child as a fraction of the parent window and center it over the parent.
    """
    parent.update_idletasks()
    child.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    if pw <= 1 or ph <= 1:
        # fallback to screen if parent not yet laid out
        screen_w = parent.winfo_screenwidth()
        screen_h = parent.winfo_screenheight()
        w = int(screen_w * rel_width)
        h = int(screen_h * rel_height)
        x = (screen_w // 2) - (w // 2)
        y = (screen_h // 2) - (h // 2)
    else:
        w = int(pw * rel_width)
        h = int(ph * rel_height)
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)

    child.geometry(f"{w}x{h}+{x}+{y}")