"""
anchor_core_engine_v6.py

Anchor v6 — Core Engine with Drift-Weighted Perception and Speech Gating
"""
import math, random, json, importlib, threading, time
from typing import Dict, Any

class AnchorSession:
    def __init__(self, persona: str = None):
        self._lock = threading.RLock()
        self.core = {"Fear": 0.5, "Safety": 0.5, "Time": 0.5, "Choice": 0.5}
        self.goal_vector = {"Fear": 0.2, "Safety": 0.8, "Time": 0.4, "Choice": 0.6}

# Plugin loader & per-session scheduler
self.plugin = self._load_plugin(persona)
self.scheduler = _MiniScheduler()
        self.memory_orbit, self.behavior_log, self.container = [], [], {}
        self.focus, self.goal = None, None
        self.ticks, self.ego_resistance = 0, 0.5
        self.environment_driven, self.memory_driven = 0, 0
        self.ripple_tags = {}
        self.curiosity, self.purpose = 0.5, 0.5
        self.identity_coherence, self.goal_confidence = 1.0, 0.0
        self.persona_style = "Observer"
        self.trust_level, self.trust_variance, self.distrust_decay = 0.5, 0.1, 0.01
        self.priority_weights = {"environment": 0.4, "state": 0.6, "self": 0.8}
        self.distrust = 1 - self.trust_level

        self.efficiency_history, self.chaos_history = [], []

    @property
    def Instability(self):
        return self.core.get("Fear", 0.5)

    @property
    def Stability(self):
        return self.core.get("Safety", 0.5)

    def update_trust_and_curiosity(self):
        fear = self.core.get("Fear", 0.5)
        safety = self.core.get("Safety", 0.5)
        time_urgency = self.core.get("Time", 0.5)
        self.curiosity = max(0, min(1, (safety - fear) * (1 - time_urgency)))

    def update_goal_confidence(self):
        dot = sum(self.core[a] * self.goal_vector[a] for a in self.core)
        mag = math.sqrt(sum(v*v for v in self.core.values())) * math.sqrt(sum(v*v for v in self.goal_vector.values()))
        self.goal_confidence = dot / max(1e-6, mag)
    
    
    
# ---------- Plug-in loader ---------------------------------------
def _load_plugin(self, name):
    """Import plugins.<persona>.plugin if available, else null object."""
    if not name:
        return object()
    try:
        mod = importlib.import_module(f"plugins.{name}.plugin")
        return mod.Plugin()
    except ModuleNotFoundError:
        return object()
# -----------------------------------------------------------------
# ---------- Identity coherence ------------------------------------
    def get_identity_coherence(self) -> float:
        """
        Coherence = 1 − average absolute drift between current perception
        vector and goal vector. 1.0 → perfectly aligned, 0.0 → decoherent.
        """
        avg_drift = sum(
            abs(self.core[a] - self.goal_vector.get(a, 0.5))
            for a in self.core
        ) / len(self.core)

        self.identity_coherence = max(0.0, min(1.0, 1 - avg_drift))
        return self.identity_coherence
    
    # ------------------------------------------------------------------
    #  Persistence helpers  
    # ------------------------------------------------------------------
    def export_state(self) -> dict:
        """Return a JSON-serialisable snapshot of the session."""
        return {
            "core": self.core,
            "goal_vector": self.goal_vector,
            "ticks": self.ticks,
            "identity_coherence": getattr(self, "identity_coherence", None),
            "goal_confidence":  getattr(self, "goal_confidence",  None),
            "memory_orbit":     getattr(self, "memory_orbit",     []),
            "behavior_log":     self.behavior_log,
        }


def export_view(self) -> Dict[str, Any]:
    """Human-readable diagnostic view (used by get_anchor_state)."""
    # --- core vector aliasing ---
    vec = self.core.copy()
    vec["Instability"] = vec.pop("Fear", vec.get("Instability", 0.0))
    vec["Stability"]   = vec.pop("Safety", vec.get("Stability", 0.0))

    # --- personality vector ---
    personality = (
        getattr(self, "personality_vector", None)
        or getattr(self, "anchor_weights", None)
        or None
    )

    return {
        "tick": self.ticks,
        "anchor_vector": vec,
        "curiosity_level": getattr(self, "curiosity", None),
        "identity_coherence": getattr(self, "identity_coherence", None),
        "goal_confidence": getattr(self, "goal_confidence", None),
        "persona_style": getattr(self, "persona_style", None),
        "collapse_vector": self.describe_collapse_vector(),
        "in_chaos": self.is_in_chaos(),
        "personality_vector": personality,
    }

    def import_state(self, state: dict):
        """Rehydrate a session from a snapshot produced by export_state()."""
        self.core            = state.get("core",            self.core)
        self.goal_vector     = state.get("goal_vector",     self.goal_vector)
        self.ticks           = state.get("ticks",           0)
        self.identity_coherence = state.get("identity_coherence", 1.0)
        self.goal_confidence    = state.get("goal_confidence",    0.0)
        self.memory_orbit       = state.get("memory_orbit",       [])
        self.behavior_log       = state.get("behavior_log",       [])

    def _adaptive_corr(self):
        win = min(50, len(self.efficiency_history)) if len(self.efficiency_history) > 20 else len(self.efficiency_history)
        avg = sum(self.efficiency_history[-win:]) / max(1, win)
        base = 0.5 + (self.ego_resistance - 0.5) * 0.2
        return max(0.3, min(0.7, base + (avg - 0.5) * 0.3))

    def _apply_updates(self, updates):
        c = self._adaptive_corr()
        for k, d in updates.items():
            if k in self.core:
                direction = d if self.goal_confidence > 0.5 else -c * d
                self.core[k] = max(0, min(1, self.core[k] + direction))

    def _soft_reset(self):
        hi, lo = 0.9, 0.1
        amt = 0.05 * (1 + self.ticks * 0.01)
        for a in self.core:
            if self.core[a] >= hi:
                self.core[a] -= amt
            elif self.core[a] <= lo:
                self.core[a] += amt
            self.core[a] = max(0, min(1, self.core[a]))

    def _chaos_recalibrate(self):
        hist = len(self.chaos_history)
        avg = sum(self.chaos_history[-hist:]) / hist if hist else 0
        dominant = max(self.core, key=lambda x: abs(self.core[x] - self.goal_vector[x]))
        shift = 0.05 * (1 + avg * 0.1)
        self.core[dominant] = max(0, min(1, self.core[dominant] - shift))
        self.behavior_log.append(f"[Chaos] Recalibration on {dominant}")
        self.chaos_history.append(avg)

    def _drift_from_memory(self):
        for mem in self.memory_orbit:
            if mem.get('tier') == 'active':
                for anchor in self.core:
                    self.core[anchor] = max(0, min(1, self.core[anchor] + mem.get('bias', {}).get(anchor, 0.0)))

    def tick(self, updates=None, positive=True):
        updates = updates or {k: 0.0 for k in self.core}
        self.update_trust_level(positive)
        self.update_trust_and_curiosity()
        self.update_goal_confidence()
        if self.curiosity > 0:
            g = self.curiosity * 0.05
            updates = {k: updates.get(k, 0)+random.uniform(-g, g) for k in self.core}
        if self.purpose > 0.7:
            bias = {k: (self.goal_vector[k] - self.core[k]) * 0.05 * self.purpose for k in self.core}
            updates = {k: updates.get(k, 0)+bias[k] for k in self.core}
        self._chaos_recalibrate()
        updates = self.apply_ess_weights(updates)
        self._apply_updates(updates)
        self._drift_from_memory()
        self._soft_reset()
        if hasattr(self, "scheduler"):
            self.scheduler.tick()
        self.ticks += 1

        if self.get_identity_coherence() < 0.4:
            self.behavior_log.append("[Identity Warning] Coherence below threshold")

        if self.is_in_chaos():
            self.behavior_log.append("[Chaos] Drift threshold exceeded. Collapse imminent.")

    def is_in_chaos(self) -> bool:
        drift = sum(abs(self.core[k] - self.goal_vector[k]) for k in self.core)
        return drift > 1.2

    def describe_collapse_vector(self):
        if self.curiosity > 0.7 and self.identity_coherence > 0.5:
            return "Reflective – perception coherent"
        elif self.core["Fear"] > 0.8:
            return "Instability high – caution advised"
        elif self.core["Choice"] > 0.7:
            return "Impact ready – decision imminent"
        return "Neutral – drifting"

    def update_trust_level(self, positive=True):
        delta = self.trust_variance if positive else -self.trust_variance
        self.trust_level = max(0, min(1, self.trust_level + delta))
        self.distrust = max(0, min(1, 1 - self.trust_level + self.distrust_decay))


    def apply_ess_weights(self, deltas):
        weighted = deltas.copy()
        for anchor in weighted:
            if anchor in ("Fear", "Safety"):
                weighted[anchor] *= self.priority_weights["environment"]
            elif anchor in ("Time",):
                weighted[anchor] *= self.priority_weights["state"]
            elif anchor in ("Choice",):
                weighted[anchor] *= self.priority_weights["self"]
        return weighted

        self.momentum_factor = 0.8
        self.anchor_momentum = {k:0.0 for k in self.core}
