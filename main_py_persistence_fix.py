"""Anchor1 API – Render‑ready entry point (Enhanced Persistence)
---------------------------------------------------------------
• Indefinite session persistence (no 24hr TTL)
• Last accessed tracking for cleanup management
• Background cleanup for abandoned sessions
"""

import os, json, time
from datetime import datetime
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import redis.asyncio as redis
import asyncio

from anchor_core_engine import AnchorSession
from api_interface import AnchorAPI
from seed import apply_seed
from seed_registry import resolve_seed
from bridge_utils import get_anchor_state

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

app = FastAPI(title="Anchor1 API (Render)", version="1.2")

# Persistence Configuration
CLEANUP_AFTER_DAYS = 90  # Clean sessions after 90 days of inactivity
CLEANUP_INTERVAL_HOURS = 24  # Run cleanup every 24 hours

# ---------- Enhanced Session Management ---------- #
async def _get_session(sid: str = "default") -> AnchorSession:
    """Load session from Redis or bootstrap from seed registry."""
    key = f"anchor:{sid}"
    cached = await redis_client.get(key)
    if cached:
        sess = AnchorSession()
        sess.import_state(json.loads(cached))
        # Update last accessed time
        await _update_last_accessed(sid)
    else:
        sess = AnchorSession()
        seed_id = resolve_seed(sid) or sid
        apply_seed(sess, seed_id, seeds_dir="seeds")
        await _update_last_accessed(sid)
    return sess

async def _save_session(sid: str, session: AnchorSession):
    """Persist session to Redis indefinitely with last accessed tracking."""
    # Save session state (NO TTL = indefinite persistence)
    await redis_client.set(
        f"anchor:{sid}",
        json.dumps(session.export_state())
        # Removed: ex=60 * 60 * 24  # No more 24hr TTL!
    )
    # Track when session was last used
    await _update_last_accessed(sid)

async def _update_last_accessed(sid: str):
    """Update the last accessed timestamp for cleanup tracking."""
    await redis_client.set(f"anchor:last_accessed:{sid}", time.time())

# ---------- Background Cleanup ---------- #
async def cleanup_abandoned_sessions():
    """Remove sessions inactive for more than CLEANUP_AFTER_DAYS."""
    cutoff_time = time.time() - (CLEANUP_AFTER_DAYS * 24 * 60 * 60)
    cleaned_count = 0
    
    # Find abandoned sessions
    last_accessed_keys = await redis_client.keys("anchor:last_accessed:*")
    
    for key in last_accessed_keys:
        timestamp = await redis_client.get(key)
        if timestamp and float(timestamp) < cutoff_time:
            # Extract session ID and clean up
            sid = key.split(":")[-1]
            await redis_client.delete(f"anchor:{sid}")
            await redis_client.delete(key)
            cleaned_count += 1
    
    print(f"Cleaned up {cleaned_count} abandoned sessions (older than {CLEANUP_AFTER_DAYS} days)")
    return cleaned_count

async def periodic_cleanup():
    """Background task for periodic session cleanup."""
    while True:
        try:
            await cleanup_abandoned_sessions()
            await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 60 * 60)
        except Exception as e:
            print(f"Cleanup error: {e}")
            await asyncio.sleep(60 * 60)  # Retry in 1 hour

@app.on_event("startup")
async def startup_event():
    """Initialize background cleanup."""
    asyncio.create_task(periodic_cleanup())
    print(f"Enhanced persistence enabled: {CLEANUP_AFTER_DAYS}-day retention")

# ---------- Original Routes (Enhanced) ---------- #
@app.get("/")
async def health():
    return {"status": "Anchor1 API running on Render (Enhanced Persistence)"}

@app.post("/send_input")
async def send_input(request: Request):
    data = await request.json()
    sid = data.get("session_id", "default")
    session = await _get_session(sid)
    result = AnchorAPI(session).send_input(data.get("input", ""))
    if data.get("show_full_state"):
        result["full_state"] = get_anchor_state(session)
    await _save_session(sid, session)
    return result

@app.post("/run_tick")
async def run_tick(request: Request):
    data = await request.json()
    sid = data.get("session_id", "default")
    session = await _get_session(sid)
    result = AnchorAPI(session).run_tick(data.get("anchor_updates", {}))
    await _save_session(sid, session)
    return result

@app.get("/get_full_state")
async def get_full_state(session_id: str = "default"):
    """Return the complete Anchor snapshot for the given session_id."""
    session = await _get_session(session_id)
    return get_anchor_state(session)

# ---------- Optional: Management Endpoints ---------- #
@app.get("/admin/cleanup_stats")
async def cleanup_stats():
    """Get session storage statistics."""
    session_keys = await redis_client.keys("anchor:*")
    session_count = len([k for k in session_keys if not k.endswith("last_accessed")])
    
    return {
        "active_sessions": session_count,
        "cleanup_after_days": CLEANUP_AFTER_DAYS,
        "next_cleanup_hours": CLEANUP_INTERVAL_HOURS
    }

@app.post("/admin/manual_cleanup")
async def manual_cleanup():
    """Manually trigger session cleanup."""
    cleaned = await cleanup_abandoned_sessions()
    return {"message": f"Cleaned {cleaned} abandoned sessions"}