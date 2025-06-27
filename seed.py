import json
import os

def apply_seed(session, seed_id='default', seeds_dir='seeds', drift_lexicons_dir='drift_lexicons'):
    """
    Unified seed loader (v3)
    --------------------------------
    • Loads personality seed <seed_id>.json from *seeds_dir*
    • Applies anchor/core vectors and extended metadata
    • Replays legacy collapse events into behavior_log
    • Optionally loads a consequence‑drift lexicon referenced by the seed
      via “consequence_drift_lexicon” **or** “consequence_drift_path”.
    Returns True if the seed was found and applied, else False.
    """

    # 1. Read seed JSON
    seed_path = os.path.join(seeds_dir, f"{seed_id}.json")
    if not os.path.exists(seed_path):
        return False

    with open(seed_path, "r", encoding="utf-8") as f:
        seed = json.load(f)

    # 2. Core / anchor vector
    vec = seed.get("last_known_vector", {})
    if "Instability" in vec or "Stability" in vec:   # hybrid label support
        inst = vec.get("Instability", session.core.get("Fear"))
        stab = vec.get("Stability", session.core.get("Safety"))
        session.core["Fear"], session.core["Safety"] = inst, stab
    for k in ("Fear", "Safety", "Time", "Choice"):
        if k in vec:
            session.core[k] = vec[k]

    # 3. Metadata passthrough
    for field in ("persona_style", "anchor_weights", "feature_flags"):
        if field in seed:
            setattr(session, field, seed[field])

    # 4. Replay collapse events
    for ev in seed.get("collapse_events", []):
        tick = ev.get("tick")
        tag = ev.get("trigger")
        if hasattr(session, "behavior_log"):
            session.behavior_log.append(f"[Seed Event @ {tick}] {tag}")

    # 5. Conditional drift‑lexicon load
    drift_key = seed.get("consequence_drift_lexicon") or seed.get("consequence_drift_path")                 or "nrc_consequence_drift.json"
    lexicon_path = os.path.join(drift_lexicons_dir, drift_key)
    if os.path.exists(lexicon_path):
        with open(lexicon_path, "r", encoding="utf-8") as lf:
            session.consequence_drift_map = json.load(lf)
            if hasattr(session, "behavior_log"):
                session.behavior_log.append(f"[Seed] Loaded drift lexicon: {drift_key}")
    else:
        session.consequence_drift_map = {}
        if hasattr(session, "behavior_log"):
            session.behavior_log.append(f"[Seed] Drift lexicon '{drift_key}' not found — empty map")

    return True
