from __future__ import annotations
import importlib
from functools import lru_cache
from typing import Dict, Any, Optional

@lru_cache(maxsize=None)
def _load_set(set_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Lazily import a P set module (e.g., 'PRB01' or 'PROMO') and return its `card_data`.
    """
    mod = importlib.import_module(f"{__name__}.{set_name}")
    return getattr(mod, "card_data", {})

def _set_from_code(code: str) -> Optional[str]:
    """
    Extract the P set name from a card code.
    Expected formats:
      - 'PRBxx-yyy' (e.g., PRB01-003)
      - 'P-xxx'     (generic promo cards inside PROMO.py)
    """
    if not code:
        return None
    if code.startswith("PRB") and len(code) >= 5:
        return code[:5]   # 'PRB01', 'PRB02', ...
    if code.startswith("P-"):
        return "PROMO"
    return None

def get_card(code: str) -> Optional[Dict[str, Any]]:
    """
    Return the card data for a single P-family card code, or None if not found.
    """
    set_name = _set_from_code(code)
    if not set_name:
        return None
    return _load_set(set_name).get(code)
