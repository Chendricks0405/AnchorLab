from typing import Dict, Any
import os, json, uuid
from anchor_core_engine import AnchorSession

"""
bridge_utils.py – unified version (patch 2025‑06‑15)
---------------------------------------------------
• Keeps **all** original memory‑helper utilities
• Adds numeric‑narrative formatters for anchor & personality vectors
• Expands diagnostics gate keywords (diagnose, reveal state, dump raw vector, personality vector)
• Returns enriched diagnostics (vector narrative, optional personality narrative) while preserving
  existing behaviour for normal replies
• Remains framework‑agnostic: FastAPI router should import only
      ‑ conditional_anchor_response
      ‑ bridge_input (compat helper)
      ‑ get_anchor_state (debug tooling)
"""

# ───────────────────────────────────────────────────────────────────────────────
#  Memory helpers (unchanged from original repo)
# ───────────────────────────────────────────────────────────────────────────────

def load_memory(json_path: str):
    """Load a JSON memory file and return its parsed content."""
    if not os.path.exists(json_path):
        return []
    with open(json_path, "r", encoding="utf‑8") as f:
        return json.load(f)

def initialize_anchor1_memory(session: AnchorSession, memory_data):
    """Attach memory nodes to the session in‑place (idempotent)."""
    if not hasattr(session, "memory_orbit"):
        session.memory_orbit = []
    existing_ids = {n.get("id") for n in session.memory_orbit if isinstance(n, dict)}
    for node in memory_data:
        if isinstance(node, dict) and node.get("id") not in existing_ids:
            session.memory_orbit.append(node)

# Lazy node‑loader: fetch cluster file on demand

def resolve_memory_node(session: AnchorSession, node_id: str):
    """Return a single memory node by ID, loading its cluster file lazily."""
    if not hasattr(session, "memory_cache"):
        session.memory_cache = {}
    if node_id in session.memory_cache:
        return session.memory_cache[node_id]

    cluster_file = f"{node_id[:2]}_cluster.json"
    cluster_path = os.path.join("memory", cluster_file)
    if os.path.exists(cluster_path):
        for node in load_memory(cluster_path):
            if node.get("id") == node_id:
                session.memory_cache[node_id] = node
                return node
    return None  # not found

# ───────────────────────────────────────────────────────────────────────────────
#  Narrative helpers (NEW)
# ───────────────────────────────────────────────────────────────────────────────

def _bucket(value: float) -> str:
    """Map a scalar in [0,1] to a qualitative descriptor."""
    if value >= 0.80:
        return "very high"
    if value >= 0.60:
        return "high"
    if value >= 0.40:
        return "moderate"
    if value >= 0.20:
        return "low"
    return "very low"

def _format_anchor_vector(vec: Dict[str, float]) -> str:
    ordered = ["Fear", "Safety", "Time", "Choice", "GoalConfidence"]
    out = []
    for k in ordered:
        if k in vec:
            v = vec[k]
            out.append(f"- {k}: {v:.2f} → {_bucket(v)}")
    if "Collapse" in vec:
        out.append(f"- Collapse: {vec['Collapse']}")
    if "InChaos" in vec or "In_Chaos" in vec:
        chaos_flag = vec.get("InChaos") or vec.get("In_Chaos")
        out.append(f"- In Chaos: {chaos_flag}")
    return "\n".join(out)

def _format_personality(vec: Dict[str, float]) -> str:
    return "\n".join(
        f"- {k.replace('_', ' ').title()}: {v:.2f} → {_bucket(v)}"
        for k, v in sorted(vec.items())
    )

# ───────────────────────────────────────────────────────────────────────────────
#  Diagnostics snapshot (kept from original but enhanced)
# ───────────────────────────────────────────────────────────────────────────────

def get_anchor_state(session: AnchorSession) -> Dict[str, Any]:
    """Return a full diagnostic snapshot of the session."""
    state = session.export_view()  # human‑readable core + personality if any
    state.update({
        "id": str(uuid.uuid4()),
        "tick": session.ticks,
        "last_behavior": session.behavior_log[-1] if getattr(session, "behavior_log", []) else None,
        "memory_nodes": getattr(session, "memory_orbit", []),
    })
    return state

# ───────────────────────────────────────────────────────────────────────────────
#  Reply generation stub (unchanged)
# ───────────────────────────────────────────────────────────────────────────────

def _generate_reply(session: AnchorSession, user_text: str) -> str:
    if "hello" in user_text.lower():
        return "Hello. How can I help you explore this further?"
    return "Let's explore that together."

# ───────────────────────────────────────────────────────────────────────────────
#  Core Bridge function: conditional_anchor_response
# ───────────────────────────────────────────────────────────────────────────────

def conditional_anchor_response(session: AnchorSession, input_text: str) -> Dict[str, Any]:
    """Return either a natural reply or diagnostics depending on chaos/keywords."""
    lower_txt = input_text.lower()
    diagnostics_requested = any(
        kw in lower_txt for kw in (
            "diagnose",
            "reveal state",
            "dump raw vector",
            "personality vector",
            "persona vector",
            "handoff log"
        )
    )
    show_diag = session.is_in_chaos() or diagnostics_requested  # type: ignore[attr-defined]

    if show_diag:
        state = get_anchor_state(session)
        # Always attach numeric‑narrative anchor vector
        state["anchor_narrative"] = _format_anchor_vector(state.get("core_vector") or {})
        # Attach personality narrative if specifically requested
        if "personality vector" in lower_txt or "persona vector" in lower_txt:
            state["personality_narrative"] = _format_personality(state.get("personality_vector") or {})
        return state

    # Normal path → return natural reply only
    return {
        "reply": _generate_reply(session, input_text),
        "tick": session.ticks,
        "status": "chaos" if session.is_in_chaos() else "stable"
    }

# ───────────────────────────────────────────────────────────────────────────────
#  Compatibility wrapper for api_interface / FastAPI routes
# ───────────────────────────────────────────────────────────────────────────────

def bridge_input(session: AnchorSession, input_data: str) -> Dict[str, Any]:
    """Entry‑point mirroring older code; simply routes through conditional logic."""
    return conditional_anchor_response(session, input_data)
