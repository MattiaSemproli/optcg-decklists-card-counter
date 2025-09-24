# opc_sets/__init__.py
from typing import Optional, Dict, Any
from . import OP, EB, ST, P

def get_card(code: str) -> Optional[Dict[str, Any]]:
    """
    Route the card code to the appropriate family loader (OP, EB, ST, P).
    """
    if not code:
        return None
    code = code.strip()
    if code.startswith("OP"):
        return OP.get_card(code)
    if code.startswith("EB"):
        return EB.get_card(code)
    if code.startswith("ST"):
        return ST.get_card(code)
    if code.startswith("PRB") or code.startswith("P-"):
        return P.get_card(code)
    return None
