from fastapi import FastAPI, Request
from startup import initialize_anchor
from anchor_core_engine import AnchorSession
from bridge_utils import bridge_input, get_anchor_state

app = FastAPI(title="Anchor1 Bridge", version="1.0")
session = initialize_anchor()

@app.get("/")
async def root():
    return {"status": "Anchor1 Bridge is running"}

@app.post("/send_input")
async def send_input(request: Request):
    data = await request.json()
    input_str = data.get("input", "")
    from bridge_utils import conditional_anchor_response
    response = bridge_input(session, input_str)
    return conditional_anchor_response(session, input_str)

@app.post("/run_tick")
async def run_tick(request: Request):
    data = await request.json()
    updates = data.get("anchor_updates", {})
    session.tick(updates)
    from bridge_utils import conditional_anchor_response
    return conditional_anchor_response(session, '[tick]')

@app.post("/config")
async def update_config(request: Request):
    data = await request.json()
    if "trust" in data:
        session.allow_trust = bool(data["trust"])
    if "curiosity" in data:
        session.allow_curiosity = bool(data["curiosity"])
    if "purpose" in data:
        session.allow_purpose = bool(data["purpose"])
    if "stability_goal" in data:
        goal = float(data["stability_goal"])
        session.stability_goal = max(0.0, min(1.0, goal))
    return {
        "status": "updated",
        "config": {
            "allow_trust": session.allow_trust,
            "allow_curiosity": session.allow_curiosity,
            "allow_purpose": session.allow_purpose,
            "stability_goal": session.stability_goal
        }
    }