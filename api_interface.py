from typing import Dict, Any
from bridge_utils import bridge_input, get_anchor_state, load_memory, initialize_anchor1_memory

class AnchorAPI:
    def __init__(self, session):
        self.session = session

    def load_memory(self, memory_file: str) -> None:
        memory_data = load_memory(memory_file)
        initialize_anchor1_memory(self.session, memory_data)

    def send_input(self, input_data: str) -> Dict[str, Any]:
        from bridge_utils import conditional_anchor_response
        response = bridge_input(self.session, input_data)
        return conditional_anchor_response(self.session, input_data)

    def run_tick(self, updates: Dict[str, float]) -> Dict[str, Any]:
        self.session.tick(updates)
        from bridge_utils import conditional_anchor_response
        return conditional_anchor_response(self.session, '[tick]')

    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        if "trust" in config:
            self.session.allow_trust = bool(config["trust"])
        if "curiosity" in config:
            self.session.allow_curiosity = bool(config["curiosity"])
        if "purpose" in config:
            self.session.allow_purpose = bool(config["purpose"])
        if "stability_goal" in config:
            goal = float(config["stability_goal"])
            self.session.stability_goal = max(0.0, min(1.0, goal))
        return {
            "status": "updated",
            "config": {
                "allow_trust": self.session.allow_trust,
                "allow_curiosity": self.session.allow_curiosity,
                "allow_purpose": self.session.allow_purpose,
                "stability_goal": self.session.stability_goal
            }
        }

    def get_full_state(self) -> Dict[str, Any]:
        from bridge_utils import conditional_anchor_response
        return conditional_anchor_response(self.session, '[tick]')