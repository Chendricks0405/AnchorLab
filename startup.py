from anchor_core_engine import AnchorSession
from seed import apply_seed
from seed_registry import resolve_seed

def initialize_anchor():
    """
    Initialize a fresh AnchorSession and load the default Explorer seed.
    Replaces previous dependency on `anchor_core_engine_v6`.
    """
    session = AnchorSession()
    # pick "therapist" as a friendly default; pull real id from registry
    seed_id = resolve_seed("therapist") or "Therapist_Seed_v1"
    loaded = apply_seed(session, seed_id=seed_id, seeds_dir="seeds")
    if loaded and hasattr(session, "behavior_log"):
        session.behavior_log.append(f"[Startup] Seed '{seed_id}' applied.")
    elif hasattr(session, "behavior_log"):
        session.behavior_log.append(f"[Startup] Seed '{seed_id}' not found.")
    return session