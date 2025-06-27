
"""
seed_registry.py
----------------
Utility functions for loading seed aliases → seed_id.

Usage:
    from seed_registry import resolve_seed

    seed_id = resolve_seed("therapist")  # → "Therapist_Seed"
    seed_id = resolve_seed("Scientist")  # case‑insensitive

The registry is stored as JSON: seeds/seed_registry.json.
"""
import json, os
from functools import lru_cache
from typing import Optional

REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "seeds", "seed_registry.json")

@lru_cache(maxsize=1)
def _load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {}
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_seed(alias: str) -> Optional[str]:
    """
    Return the canonical seed_id matching *alias* (case‑insensitive).
    If no match found, returns None.
    """
    registry = _load_registry()
    return registry.get(alias.lower())
