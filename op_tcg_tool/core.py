# core.py
# Helpers: parsing, local DB access, aggregation, grouping. Code/comments in English.

import csv
from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs

# Optional cards DB accessor
try:
    from opc_sets import get_card
except Exception:
    def get_card(code: str):
        return None

# ---------- terminal pretties (only for CLI fallback) ----------
try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
    COLOR_RED = Fore.RED
    COLOR_RESET = Style.RESET_ALL
except Exception:
    COLOR_RED = "\033[31m"
    COLOR_RESET = "\033[0m"

def print_error(msg: str) -> None:
    """Print a red error line without stopping the program."""
    print(f"{COLOR_RED}{msg}{COLOR_RESET}")

# ---------- card helpers ----------
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

def card_cost(info: dict):
    """Extract numeric Generic cost if available; otherwise return None."""
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

def card_power(info: dict):
    """Return numeric Power if present, else None."""
    if not info:
        return None
    p = info.get('Power')
    if p is None or str(p).strip() == "":
        return None
    try:
        return int(p)
    except Exception:
        try:
            return int(float(p))
        except Exception:
            return None

def card_colors(info: dict):
    """Return list of color strings."""
    colors = (info or {}).get('Color')
    if isinstance(colors, list):
        return [str(c) for c in colors]
    if isinstance(colors, str) and colors.strip():
        return [colors.strip()]
    return []

def card_color_str(info: dict) -> str:
    """Return display string for colors (joined with '/')."""
    cols = card_colors(info)
    return " / ".join(cols) if cols else ""

def is_leader(info: dict) -> bool:
    return get_category(info) == 'leader'

def card_name(info: dict, fallback_id: str) -> str:
    """Return Name -> Card Name -> card ID as fallback."""
    if not info:
        return fallback_id
    return (info.get("Name") or info.get("Card Name") or fallback_id)

# ---------- parsing ----------
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

# ---------- leader inference & grouping ----------
def infer_deck_leader(deck: dict):
    """
    Given a single deck {card_id: count}, return (leader_id, leader_name, leader_colors_list) if any;
    otherwise (None, None, []).
    """
    for cid in deck:
        info = get_card(cid) or {}
        if is_leader(info):
            return cid, card_name(info, cid), card_colors(info)
    return None, None, []

def group_decks_by_leader(decks):
    """
    Partition decks by inferred leader ID.
    Returns:
      groups: dict[leader_id_or_None] -> list[deck]
      meta: dict[leader_id_or_None] -> {"name": str|None, "colors": list[str]}
    Decks with no detectable leader are grouped under key None.
    """
    from collections import defaultdict as _df
    groups = _df(list)
    meta = {}
    for d in decks:
        lid, lname, lcols = infer_deck_leader(d)
        groups[lid].append(d)
        if lid not in meta:
            meta[lid] = {"name": lname, "colors": lcols}
    return groups, meta

# ---------- aggregation ----------
def summarize_decks(decks):
    """
    Aggregate stats across decks (leaders are EXCLUDED from the rows).
    Returns:
      rows: list of tuples (avg, occ, total, id, name, cost_val, color_str, power_val, cat, crank)
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

    # detect a leader just for header (may be None)
    lid, leader_name_val, colors = infer_deck_leader(decks[0]) if decks else (None, None, [])

    rows = []
    for cid in total_counts:
        info = get_card(cid) or {}
        cat = get_category(info)
        if cat == "leader":
            continue  # exclude leaders from rows

        nm = card_name(info, cid)
        cval = card_cost(info)          # numeric or None
        pval = card_power(info)         # numeric or None
        colstr = card_color_str(info)   # "Red", "Blue / Green", ...
        crank = category_rank(cat)
        total = total_counts[cid]
        occ = occurrence[cid]
        avg_all = total / num_decks
        rows.append((avg_all, occ, total, cid, nm, cval, colstr, pval, cat, crank))

    # default order: by category group, then by avg desc, then occ desc, then ID
    rows.sort(key=lambda r: (r[9], -r[0], -r[1], r[3]))

    header = f"Decks analyzed: {num_decks}"
    if colors:
        header += f" | Colors: {' / '.join(colors[:2])}"
    if leader_name_val:
        header += f" | Leader: {leader_name_val}"

    return rows, header, leader_name_val, colors
