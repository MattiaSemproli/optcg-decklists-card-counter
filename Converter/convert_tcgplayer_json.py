
import re, json, html, argparse, importlib.util, sys, os
from types import ModuleType

def ed_lookup(extended, key):
    for item in extended or []:
        if item.get("name") == key or item.get("displayName") == key:
            return item.get("value")
    return None

def clean_text(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s

def extract_trigger(description):
    if not description:
        return ""
    m = re.search(r"\[Trigger\]\s*(.*)", description, flags=re.I|re.S)
    if not m:
        return ""
    rest = m.group(1)
    cut = re.split(r"\s*\[[^\]]+\]", rest, maxsplit=1)
    trigger = cut[0].strip(" :;\n\r\t")
    return clean_text(trigger)

def titlecase_slug(slug):
    words = slug.split("-")
    return " ".join(w.capitalize() if not re.fullmatch(r"[ivx]+", w) else w.upper() for w in words)

def normalize_set(url, ext, product_name=""):
    # Prefer explicit Set-like fields
    for k in ("Set", "Set Name", "SetName", "Set name"):
        v = ed_lookup(ext, k)
        if v:
            base = re.sub(r"\s+", " ", v).strip(" -")
            return base

    set_str = ""
    if url:
        m = re.search(r"/one-piece-card-game-([a-z0-9\-]+)-", url)
        if m:
            slug = m.group(1)
            if slug.startswith("starter-deck"):
                body = re.sub(r"^starter-deck-\d+-", "", slug)
                set_str = f"STARTER DECK -{titlecase_slug(body)}-"
            elif slug.startswith("theme-booster"):
                body = re.sub(r"^theme-booster-", "", slug)
                set_str = f"THEME BOOSTER -{titlecase_slug(body)}-"
            elif slug.startswith("booster-pack-"):
                body = re.sub(r"^booster-pack-", "", slug)
                set_str = f"BOOSTER PACK -{titlecase_slug(body)}-"
            else:
                set_str = f"BOOSTER PACK -{titlecase_slug(slug)}-"
    if not set_str and product_name and " - " in product_name:
        set_str = product_name.split(" - ")[0].strip()
    return set_str

def variant_rank(name):
    n = (name or "").lower()
    if "parallel" in n or "alt art" in n or "alternate" in n or "manga" in n:
        return 2
    if "box topper" in n or "promo" in n:
        return 3
    return 1

def art_index_from_name(name):
    n = (name or "").lower()
    if "parallel" in n:
        return 2
    if "alt art" in n or "alternate" in n or "manga" in n:
        return 3
    if "box topper" in n:
        return 4
    return 1

def load_card_data_from_module(path):
    try:
        spec = importlib.util.spec_from_file_location("opcards", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        if hasattr(mod, "card_data") and isinstance(mod.card_data, dict):
            return mod.card_data
    except Exception as e:
        print(f"Warning: could not import card_data from {path}: {e}", file=sys.stderr)
    return {}

def convert(input_json, strategy="base", merge_art_from=None):
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Optional Art merge source
    art_merge = {}
    if merge_art_from:
        art_merge = load_card_data_from_module(merge_art_from)

    card_data = {}
    picked_rank = {}  # used only for strategy=base

    for item in data.get("results", []):
        ext = item.get("extendedData", [])
        number = ed_lookup(ext, "Number")
        if not number:
            continue  # skip non-cards

        rarity = ed_lookup(ext, "Rarity") or ""
        description_raw = ed_lookup(ext, "Description") or ""
        color_raw = ed_lookup(ext, "Color") or ""
        cardtype = ed_lookup(ext, "CardType") or ""
        cost_raw = ed_lookup(ext, "Cost") or "0"
        power_raw = ed_lookup(ext, "Power") or "0"
        counter_raw = ed_lookup(ext, "Counter") or ed_lookup(ext, "Counterplus") or "0"
        subtypes_raw = ed_lookup(ext, "Subtypes") or ""

        parts = number.split("-")
        card_id = parts if len(parts)==2 else [number, ""]

        color_list = [c.strip() for c in color_raw.split(";") if c.strip()] if color_raw else []
        type_list = [t.strip() for t in subtypes_raw.split(";") if t.strip()] if subtypes_raw else []

        effect = clean_text(description_raw or "")
        trigger = extract_trigger(description_raw)

        def to_int(x):
            try:
                return int(str(x).strip())
            except:
                return 0

        cost_generic = to_int(cost_raw)
        power_val = to_int(power_raw)
        counter_val = to_int(counter_raw)

        name = item.get("name") or ""
        name_clean = re.sub(r"\s*\((?:Parallel|Box Topper|Alternate Art|Manga|Promo|[0-9]+|.*?)\)\s*$", "", name, flags=re.I).strip()

        category = {"Leader":"Leader","Character":"Character","Event":"Event","Stage":"Stage"}.get(cardtype, cardtype or "")

        set_name = normalize_set(item.get("url",""), ext, product_name=item.get("name",""))

        # Compose record now (Art may be overridden below)
        record = {
            "CARD ID": card_id,
            "Rarity": rarity,
            "Category": category,
            "Card Name": name_clean,
            "Cost": {"Generic": cost_generic},
            "Power": power_val,
            "Counter": counter_val,
            "Color": color_list,
            "Type": type_list,
            "Effect": effect if effect else "-",
            "Art": art_index_from_name(name),
            "Trigger": trigger,
            "Set": set_name
        }

        if strategy == "first":
            if number not in card_data:
                card_data[number] = record
        else:  # strategy == "base" (prefer non-parallel variants)
            vrank = variant_rank(name)
            prev = picked_rank.get(number)
            if prev is None or vrank < prev:
                card_data[number] = record
                picked_rank[number] = vrank

    # Optional: merge Art indices from an existing module
    if art_merge:
        for k, rec in card_data.items():
            try:
                src = art_merge.get(k)
                if src and isinstance(src, dict) and "Art" in src:
                    rec["Art"] = src["Art"]
            except Exception:
                pass

    return card_data

def write_module(card_data, output_py):
    with open(output_py, "w", encoding="utf-8") as f:
        f.write("card_data = ")
        f.write(json.dumps(card_data, indent=4, ensure_ascii=False))

def main():
    p = argparse.ArgumentParser(description="Convert TCGplayer JSON dump to a Python module with card_data.")
    p.add_argument("input_json", help="Path to input JSON file (TCGplayer dump).")
    p.add_argument("output_py", help="Path to output .py module to write.")
    p.add_argument("--strategy", choices=["base","first"], default="base",
                   help="De-dup strategy when multiple versions exist for the same card code. 'base' prefers non-parallel/alt; 'first' keeps the first encountered.")
    p.add_argument("--merge-art-from", dest="merge_art_from", default=None,
                   help="Path to a Python module containing card_data to copy Art indices from (e.g., opcardlist.py).")
    args = p.parse_args()

    card_data = convert(args.input_json, strategy=args.strategy, merge_art_from=args.merge_art_from)
    write_module(card_data, args.output_py)

if __name__ == "__main__":
    main()
