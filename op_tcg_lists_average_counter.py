import re
from collections import defaultdict, Counter
import tkinter as tk
from datetime import datetime
from pathlib import Path
import numpy as np
from urllib.parse import urlparse, parse_qs

# --- your local cards DB accessor ---
try:
    from opc_sets import get_card
except Exception:  # fallback for testing without the package
    def get_card(code: str):
        return None

# --------------------------- helpers ---------------------------
def format_card_stats(card_info: dict) -> str:
    """
    Build a compact stat string for the table.
    - For Events: [Event]
    - Otherwise prefer Power; then Generic Cost; else '—'
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
    """
    Always return something for the 'Name' column:
    try 'Name' -> 'Card Name' -> fallback to the card ID.
    """
    if not info:
        return fallback_id
    return (info.get("Name") or info.get("Card Name") or fallback_id)

# --------------------------- deckgen parsing ---------------------------
def parse_deckgen_url(url: str):
    """
    Parse a onepiecetopdecks deckgen URL and return a list of (card_id, count).
    Uses the 'dg' query param which encodes like: 1nOP03-040a4nOP03-044...
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
            if not cnt_str.isdigit():
                continue
            out.append((code.strip(), int(cnt_str)))
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

# --------------------------- summary ---------------------------
def summarize_decks(decks):
    """
    Aggregate stats across decks.
    Returns: (output_text, leader_name, colors)
    """
    if not decks:
        return "No valid lists found.", None, []

    num_decks = len(decks)
    total_counts = Counter()
    occurrence = Counter()  # in how many decks the card appears
    for d in decks:
        total_counts.update(d)
        for cid in d:
            occurrence[cid] += 1

    # Try to infer leader (first leader found across decks)
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

    # Prepare rows: average across ALL decks (missing = 0)
    rows = []
    for cid in total_counts:
        info = get_card(cid) or {}
        name = card_name(info, cid)  # << supports "Card Name" too
        stat = format_card_stats(info)
        total = total_counts[cid]
        occ = occurrence[cid]
        avg_all = total / num_decks
        rows.append((avg_all, occ, total, cid, name, stat))

    # sort by avg desc, then occurrence desc, then card id
    rows.sort(key=lambda x: (-x[0], -x[1], x[3]))

    # build table
    header = f"Lists analyzed: {num_decks}"
    if colors:
        header += f" | Colors: {' / '.join(colors[:2])}"
    if leader_name_val:
        header += f" | Leader: {leader_name_val}"
    header += "\n"

    col_names = ["Avg", "Occ", "Total", "ID", "Name", "Stat"]
    fmt = "{:>5}  {:>4}  {:>6}  {:<10}  {:<32}  {:<8}"

    lines = [header, fmt.format(*col_names), "-" * 80]
    for avg, occ, total, cid, name, stat in rows:
        lines.append(fmt.format(f"{avg:.2f}", str(occ), str(total), cid, name[:32], stat))

    return "\n".join(lines), leader_name_val, colors

# --------------------------- UI ---------------------------
def display_output(output_text: str, leader: str | None, colors: list[str]):
    root = tk.Tk()
    title_bits = ["Decklists Summary"]
    if colors:
        title_bits.append(" / ".join(colors[:2]))
    if leader:
        title_bits.append(leader)
    root.title(" : ".join(title_bits))

    output_text = "\n" + (output_text or "(no data)")

    text = tk.Text(root, wrap="none", font=("Consolas", 10), bg="white")
    text.insert("1.0", output_text)
    text.configure(state="disabled")

    xscroll = tk.Scrollbar(root, orient="horizontal", command=text.xview)
    yscroll = tk.Scrollbar(root, orient="vertical", command=text.yview)
    text.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)

    text.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    xscroll.grid(row=1, column=0, sticky="ew")

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    root.mainloop()

# --------------------------- main ---------------------------
def main():
    print("Paste one deckgen link per line.")
    print("Press ENTER on an empty line to finish.\n")

    urls = []
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        urls.append(line)

    decks = decks_from_urls(urls)
    output_text, leader, colors = summarize_decks(decks)

    print("\n" + output_text + "\n")
    try:
        display_output(output_text, leader, colors)
    except Exception:
        # Ignore Tkinter in headless environments
        pass

    # filename
    dt_string = datetime.now().strftime("%d%m%Y_%H%M%S")
    leader_sanitized = (leader or "Leader").replace(" ", "_")
    color_tag = "_".join(colors[:2]) if colors else "Colors"
    filename = f"{color_tag}_{leader_sanitized}_{dt_string}.txt"

    save = input("Save output to file? (y/n): ").strip().lower()
    if save == "y":
        outdir = Path("output")
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / filename
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"Saved: {outfile.resolve()}")
    else:
        print("Output not saved.")

if __name__ == "__main__":
    main()
