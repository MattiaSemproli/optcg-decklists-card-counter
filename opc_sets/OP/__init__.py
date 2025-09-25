from __future__ import annotations
import importlib
from functools import lru_cache
from typing import Dict, Any, Optional

@lru_cache(maxsize=None)
def _load_set(set_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Lazily import an OP set module (e.g., 'OP01') and return its `card_data` dict.
    Each set is imported only once thanks to caching.
    """
    mod = importlib.import_module(f"{__name__}.{set_name}")
    return getattr(mod, "card_data", {})

def _set_from_code(code: str) -> Optional[str]:
    """
    Extract the OP set name from a card code.
    Expected format: 'OPxx-yyy' (e.g., OP01-095).
    """
    if not code or not code.startswith("OP") or len(code) < 4:
        return None
    return code[:4]  # 'OP01', 'OP12', ...

def get_card(code: str) -> Optional[Dict[str, Any]]:
    """
    Return the card data for a single OP card code, or None if not found.
    """
    set_name = _set_from_code(code)
    if not set_name:
        return None
    return _load_set(set_name).get(code)
