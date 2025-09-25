# core.py
# Code and comments in ENGLISH, as requested.

from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Tuple, Optional

# -------------- optional cards DB accessor --------------
try:
    from opc_sets import get_card
except Exception:
    def get_card(code: str):
        return None

# -------------- console helper --------------
def print_error(msg: str) -> None:
    print(f"\033[31m{msg}\033[0m")

# -------------- card helpers --------------
def get_category(info: dict) -> str:
    """Return normalized category string ('character','event','stage','leader',...)."""
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

def format_card_stats(card_info: dict) -> str:
    """
    Display rule for the 'Stat' column:
      - Events -> "[Event]"
      - All others -> show Counter as CXXXX (e.g., C2000, C1000, C0 if no counter)
    """
    if not card_info:
        return "—"
    if get_category(card_info) == "event":
        return "[Event]"
    if get_category(card_info) == "stage":
        return "[Stage]"

    # Parse Counter -> int; if missing/non-numeric, treat as 0
    ctr = card_info.get("Counter", 0)
    val = 0
    if ctr is not None and str(ctr).strip() != "":
        try:
            val = int(ctr)
        except Exception:
            try:
                val = int(float(ctr))
            except Exception:
                val = 0
    return f"C{val}"

def card_cost(info: dict) -> Optional[int]:
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

def is_leader(card_info: dict) -> bool:
    return get_category(card_info) == 'leader'

def get_colors(card_info: dict) -> List[str]:
    colors = (card_info or {}).get('Color')
    if isinstance(colors, list):
        return [str(c) for c in colors]
    if isinstance(colors, str) and colors.strip():
        return [colors.strip()]
    return []

def card_name(info: dict, fallback_id: str) -> str:
    """Return display name: try 'Name' -> 'Card Name' -> fallback to card ID."""
    if not info:
        return fallback_id
    return (info.get("Name") or info.get("Card Name") or fallback_id)

# -------------- deckgen parsing --------------
def parse_deckgen_url(url: str) -> List[Tuple[str, int]]:
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

def decks_from_urls(urls: List[str]) -> List[Dict[str, int]]:
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

# -------------- grouping by leader --------------
def group_decks_by_leader(decks: List[Dict[str, int]]):
    """
    Group deck dicts by detected leader ID (first Leader found in each deck).
    Returns:
      groups: dict[leader_id_or_NO_LEADER] -> list[deck dict]
      meta: dict with optional helpful info (currently empty, kept for API compat)
    """
    groups: Dict[str, List[Dict[str, int]]] = defaultdict(list)
    for d in decks:
        leader_id = "NO_LEADER"
        for cid in d.keys():
            info = get_card(cid) or {}
            if is_leader(info):
                leader_id = cid
                break
        groups[leader_id].append(d)
    return dict(groups), {}

# -------------- aggregation with per-deck breakdown --------------
def summarize_decks_with_breakdown(decks):
    """
    Aggregate stats across decks and also return per-card per-deck counts.
    Returns:
      rows: list of tuples (avg, occ, total, id, name, cost_val, stat, cat, crank)
      header_text: str
      leader_name_val: str|None
      colors: list[str]
      perdeck_counts: dict[str, list[int]]   # card_id -> [counts per deck where count>0]
      total_counts: dict[str, int]           # card_id -> total copies across group
    """
    if not decks:
        return [], "No valid lists found.", None, [], {}, {}

    num_decks = len(decks)
    total_counts = Counter()
    occurrence = Counter()

    # per-deck counts (store only positive counts)
    perdeck_counts = defaultdict(list)

    for d in decks:
        total_counts.update(d)
        for cid, c in d.items():
            if c > 0:
                perdeck_counts[cid].append(c)
        for cid in d:
            occurrence[cid] += 1

    # detect leader & colors from first deck that has a leader
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
        if is_leader(info):
            continue  # exclude leaders from rows
        nm = card_name(info, cid)
        stat = format_card_stats(info)
        cval = card_cost(info)
        cat = get_category(info)
        crank = category_rank(cat)
        total = total_counts[cid]
        occ = occurrence[cid]
        avg_all = total / num_decks
        rows.append((avg_all, occ, total, cid, nm, cval, stat, cat, crank))

    # order: by category group, then avg desc, then occ desc, then ID
    rows.sort(key=lambda r: (r[8], -r[0], -r[1], r[3]))

    header = f"Decks analyzed: {num_decks}"
    if colors:
        header += f" | Colors: {' / '.join(colors[:2])}"
    if leader_name_val:
        header += f" | Leader: {leader_name_val}"

    return rows, header, leader_name_val, colors, dict(perdeck_counts), dict(total_counts)
