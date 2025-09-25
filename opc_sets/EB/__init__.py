from __future__ import annotations
import importlib
from functools import lru_cache
from typing import Dict, Any, Optional

@lru_cache(maxsize=None)
def _load_set(set_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Lazily import an EB set module (e.g., 'EB01') and return its `card_data`.
    """
    mod = importlib.import_module(f"{__name__}.{set_name}")
    return getattr(mod, "card_data", {})

def _set_from_code(code: str) -> Optional[str]:
    """
    Extract the EB set name from a card code.
    Expected format: 'EBxx-yyy' (e.g., EB02-045).
    """
    if not code or not code.startswith("EB") or len(code) < 4:
        return None
    return code[:4]

def get_card(code: str) -> Optional[Dict[str, Any]]:
    """
    Return the card data for a single EB card code, or None if not found.
    """
    set_name = _set_from_code(code)
    if not set_name:
        return None
    return _load_set(set_name).get(code)
