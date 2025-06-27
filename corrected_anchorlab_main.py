# anchorlab_main.py
"""
AnchorLab.ai - AI Personality Marketplace API
=============================================
Scientific AI personality generation and mixing platform
Built on proven Anchor Vector technology
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import redis.asyncio as redis
from dotenv import load_dotenv

# Import our core systems (using your actual files)
from anchor_core_engine import AnchorSession
from memory_system_implementation import EnhancedMemorySystem
from personality_mixer import PersonalityMixer
from api_interface import AnchorAPI
from bridge_utils import get_anchor_state, bridge_input

load_dotenv()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
ANCHORLAB_VERSION = "1.0.0"

# Persistence Configuration
CLEANUP_AFTER_DAYS = 90  # Clean sessions after 90 days of inactivity
CLEANUP_INTERVAL_HOURS = 24  # Run cleanup every 24 hours

# Initialize FastAPI with AnchorLab branding
app = FastAPI(
    title="AnchorLab.ai API",
    description="Scientific AI Personality Marketplace - Create, Mix, and Deploy Measured AI Personalities",
    version=ANCHORLAB_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

# Global systems
personality_mixer = PersonalityMixer()

# Pydantic models
class PersonalityRequest(BaseModel):
    name: str
    big5_scores: Dict[str, float]
    mfd_scores: Optional[Dict[str, float]] = None
    goal_statement: Optional[str] = None
    persona_style: Optional[str] = None
    domain: Optional[str] = "emotional"

class MixRequest(BaseModel):
    combinations: List[List]  # [["personality_name", weight], ...]
    custom_goal: Optional[str] = None

class SessionRequest(BaseModel):
    session_id: str
    personality_seed: Optional[str] = None
    user_input: Optional[str] = None

class AnchorUpdateRequest(BaseModel):
    session_id: str
    anchor_updates: Dict[str, float]

# ---------- Enhanced Session Management ---------- #
async def _get_session(sid: str = "default") -> AnchorSession:
    """Load session from Redis or create new session."""
    key = f"anchorlab:session:{sid}"
    cached = await redis_client.get(key)
    if cached:
        sess = AnchorSession()
        sess.import_state(json.loads(cached))
        # Update last accessed time
        await _update_last_accessed(sid)
    else:
        sess = AnchorSession()
        await _update_last_accessed(sid)
    return sess

async def _save_session(sid: str, session: AnchorSession):
    """Persist session to Redis indefinitely with last accessed tracking."""
    # Save session state (NO TTL = indefinite persistence)
    await redis_client.set(
        f"anchorlab:session:{sid}",
        json.dumps(session.export_state())
    )
    # Track when session was last used
    await _update_last_accessed(sid)

async def _update_last_accessed(sid: str):
    """Update the last accessed timestamp for cleanup tracking."""
    await redis_client.set(f"anchorlab:last_accessed:{sid}", time.time())

# ---------- Background Cleanup ---------- #
async def cleanup_abandoned_sessions():
    """Remove sessions inactive for more than CLEANUP_AFTER_DAYS."""
    cutoff_time = time.time() - (CLEANUP_AFTER_DAYS * 24 * 60 * 60)
    cleaned_count = 0
    
    # Find abandoned sessions
    last_accessed_keys = await redis_client.keys("anchorlab:last_accessed:*")
    
    for key in last_accessed_keys:
        timestamp = await redis_client.get(key)
        if timestamp and float(timestamp) < cutoff_time:
            # Extract session ID and clean up
            sid = key.split(":")[-1]
            await redis_client.delete(f"anchorlab:session:{sid}")
            await redis_client.delete(key)
            cleaned_count += 1
    
    print(f"🧹 Cleaned up {cleaned_count} abandoned sessions (older than {CLEANUP_AFTER_DAYS} days)")
    return cleaned_count

async def periodic_cleanup():
    """Background task for periodic session cleanup."""
    while True:
        try:
            await cleanup_abandoned_sessions()
            await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 60 * 60)
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            await asyncio.sleep(60 * 60)  # Retry in 1 hour

# ---------- Startup/Shutdown ---------- #
@app.on_event("startup")
async def startup_event():
    """Initialize AnchorLab systems"""
    try:
        # Test Redis connection
        await redis_client.ping()
        print("✓ Redis connected")
        
        # Load personality foundations
        personality_mixer.load_foundation_personalities()
        print("✓ Foundation personalities loaded")
        
        # Start background cleanup
        asyncio.create_task(periodic_cleanup())
        print("✓ Background cleanup started")
        
        print(f"🚀 AnchorLab.ai v{ANCHORLAB_VERSION} started successfully")
        print(f"🔬 Enhanced persistence enabled: {CLEANUP_AFTER_DAYS}-day retention")
        
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await redis_client.close()
    print("👋 AnchorLab.ai shutdown complete")

# ---------- Core Routes ---------- #
@app.get("/")
async def root():
    """Health check and system info"""
    return {
        "service": "AnchorLab.ai",
        "version": ANCHORLAB_VERSION,
        "description": "Scientific AI Personality Marketplace",
        "tagline": "Where AI Personalities Are Born",
        "status": "operational",
        "features": [
            "Scientific personality generation (Big 5 + Moral Foundations)",
            "Domain-agnostic language mapping (Finance, CyberSec, Healthcare)", 
            "Personality mixing engine (20 foundation personalities)",
            "Enhanced anchor vector measurement",
            "Persistent memory systems",
            "Autonomous agent integration"
        ],
        "endpoints": {
            "personalities": "/api/personalities",
            "mixer": "/api/mix",
            "sessions": "/api/sessions",
            "anchor_updates": "/api/anchor/tick",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test Redis
        redis_ping = await redis_client.ping()
        
        # Test personality system
        foundation_count = len(personality_mixer.base_personalities)
        
        # Get session count
        session_keys = await redis_client.keys("anchorlab:session:*")
        active_sessions = len(session_keys)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "redis": "connected" if redis_ping else "disconnected",
            "foundation_personalities": foundation_count,
            "active_sessions": active_sessions,
            "version": ANCHORLAB_VERSION,
            "anchor_technology": "operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ---------- Personality Generation ---------- #
@app.get("/api/personalities")
async def list_personalities():
    """List all available foundation personalities"""
    personalities = {}
    for name, config in personality_mixer.base_personalities.items():
        personalities[name] = {
            "name": name,
            "goal_statement": config.get("goal_statement", ""),
            "persona_style": config.get("persona_style", ""),
            "anchor_vector": config.get("core_vector_default", {}),
            "personality_traits": config.get("personality_vector", {}),
            "memory_nodes": config.get("memory_scaffolding", {}).get("root_nodes", [])
        }
    
    return {
        "personalities": personalities,
        "count": len(personalities),
        "mixing_combinations": f"{len(personalities) * (len(personalities) - 1)} possible pairs",
        "total_combinations": f"{2**len(personalities) - 1} total possible mixes"
    }

@app.post("/api/personalities/generate")
async def generate_personality(request: PersonalityRequest):
    """Generate a custom personality seed using AnchorLab technology"""
    try:
        # Create anchor session with domain support
        session = AnchorSession(domain=request.domain)
        
        # Apply Big 5 scores to anchor vector (simplified mapping)
        if request.big5_scores:
            # Map Big 5 to anchor vector using established cognitive science
            fear_component = 1.0 - request.big5_scores.get("neuroticism_volatility", 0.5)
            safety_component = request.big5_scores.get("agreeableness_compassion", 0.5)
            time_component = request.big5_scores.get("conscientiousness_industriousness", 0.5)
            choice_component = request.big5_scores.get("openness_intellect", 0.5)
            
            session.core = {
                "Fear": fear_component,
                "Safety": safety_component, 
                "Time": time_component,
                "Choice": choice_component
            }
        
        # Generate personality seed
        personality_seed = {
            "seed_id": f"Custom_{request.name}_{int(time.time())}",
            "created": datetime.now().isoformat(),
            "goal_statement": request.goal_statement or f"Custom personality: {request.name}",
            "persona_style": request.persona_style or f"Custom {request.name} personality",
            "core_vector_default": session.core.copy(),
            "personality_vector": request.big5_scores,
            "moral_foundations": request.mfd_scores or {},
            "domain": request.domain,
            "memory_scaffolding": {"root_nodes": [f"CUST_{request.name[:3].upper()}001"]},
            "constraints": {"reply_hygiene": f"Embody {request.name} personality traits."},
            "consequence_drift_lexicon": "MFD2.0_consequence_drift.json"
        }
        
        return {
            "success": True,
            "personality_seed": personality_seed,
            "anchor_diagnostics": session.export_view(),
            "domain_anchors": session.get_domain_anchors() if hasattr(session, 'get_domain_anchors') else {}
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Generation failed: {str(e)}")

@app.post("/api/personalities/mix")
async def mix_personalities(request: MixRequest):
    """Mix multiple foundation personalities using AnchorLab's personality mixer"""
    try:
        # Convert list format to tuple format for mixer
        combinations = [(name, weight) for name, weight in request.combinations]
        
        mixed_personality = personality_mixer.mix_personalities(
            combinations=combinations,
            custom_goal=request.custom_goal
        )
        
        return {
            "success": True,
            "mixed_personality": mixed_personality,
            "source_combinations": combinations,
            "anchor_analysis": "Mixed using weighted anchor vector blending",
            "marketplace_ready": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mixing failed: {str(e)}")

# ---------- Session Management ---------- #
@app.post("/api/sessions/create")
async def create_session(request: SessionRequest):
    """Create new anchor session with personality"""
    try:
        session_id = request.session_id
        
        # Create session with optional personality seed
        session = AnchorSession(persona=request.personality_seed)
        memory_system = EnhancedMemorySystem()
        
        # Store session in Redis
        session_data = {
            "anchor_state": session.export_view(),
            "memory_stats": memory_system.get_memory_stats(),
            "created_at": datetime.now().isoformat(),
            "personality_seed": request.personality_seed,
            "session_type": "anchorlab_marketplace"
        }
        
        await redis_client.set(
            f"anchorlab:session:{session_id}",
            json.dumps(session.export_state()),
        )
        
        # Also store session metadata
        await redis_client.set(
            f"anchorlab:meta:{session_id}",
            json.dumps(session_data),
            ex=60 * 60 * 24 * 7  # 7 day TTL for metadata
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "session_data": session_data,
            "anchor_diagnostics": session.export_view()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Session creation failed: {str(e)}")

@app.post("/api/sessions/{session_id}/interact")
async def interact_with_session(session_id: str, request: SessionRequest):
    """Interact with an existing session using AnchorLab bridge"""
    try:
        # Retrieve session
        session = await _get_session(session_id)
        
        # Use AnchorLab bridge for interaction
        result = bridge_input(session, request.user_input or "")
        
        # Save updated session
        await _save_session(session_id, session)
        
        # Enhanced response with anchor diagnostics
        response = {
            "session_id": session_id,
            "user_input": request.user_input,
            "ai_response": result.get("reply", "Response generated"),
            "anchor_state": session.core.copy(),
            "anchor_diagnostics": session.export_view(),
            "timestamp": datetime.now().isoformat(),
            "chaos_status": "chaos" if session.is_in_chaos() else "stable"
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interaction failed: {str(e)}")

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information and diagnostics"""
    try:
        session = await _get_session(session_id)
        
        # Get metadata if available
        meta_data = await redis_client.get(f"anchorlab:meta:{session_id}")
        metadata = json.loads(meta_data) if meta_data else {}
        
        return {
            "session_id": session_id,
            "anchor_state": session.core.copy(),
            "anchor_diagnostics": session.export_view(),
            "metadata": metadata,
            "domain_anchors": session.get_domain_anchors() if hasattr(session, 'get_domain_anchors') else {}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session retrieval failed: {str(e)}")

# ---------- Anchor System Routes ---------- #
@app.post("/api/anchor/tick")
async def run_anchor_tick(request: AnchorUpdateRequest):
    """Run anchor tick with updates - core AnchorLab functionality"""
    try:
        session = await _get_session(request.session_id)
        
        # Use AnchorAPI for tick
        api = AnchorAPI(session)
        result = api.run_tick(request.anchor_updates)
        
        # Save updated session
        await _save_session(request.session_id, session)
        
        return {
            "success": True,
            "session_id": request.session_id,
            "tick_result": result,
            "anchor_updates_applied": request.anchor_updates,
            "new_anchor_state": session.core.copy(),
            "chaos_status": "chaos" if session.is_in_chaos() else "stable"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anchor tick failed: {str(e)}")

@app.get("/api/anchor/state/{session_id}")
async def get_anchor_state_full(session_id: str):
    """Get complete anchor state diagnostics"""
    try:
        session = await _get_session(session_id)
        
        return {
            "session_id": session_id,
            "full_anchor_state": get_anchor_state(session),
            "core_vector": session.core.copy(),
            "goal_vector": session.goal_vector.copy(),
            "ticks": session.ticks,
            "chaos_analysis": {
                "in_chaos": session.is_in_chaos(),
                "chaos_score": "calculated" if hasattr(session, '_calculate_enhanced_chaos_score') else "basic"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anchor state retrieval failed: {str(e)}")

# ---------- Analytics & Management ---------- #
@app.get("/api/analytics/overview")
async def get_analytics():
    """Get AnchorLab system analytics"""
    try:
        # Get all session keys
        session_keys = await redis_client.keys("anchorlab:session:*")
        
        # Basic analytics
        active_sessions = len(session_keys)
        personality_usage = {}
        
        # Sample some sessions for usage stats
        for key in session_keys[:50]:  # Sample first 50
            try:
                meta_id = key.replace("session", "meta")
                session_data = await redis_client.get(meta_id)
                if session_data:
                    data = json.loads(session_data)
                    personality = data.get("personality_seed", "unknown")
                    personality_usage[personality] = personality_usage.get(personality, 0) + 1
            except:
                continue
        
        return {
            "service": "AnchorLab.ai",
            "active_sessions": active_sessions,
            "personality_usage": personality_usage,
            "foundation_personalities": len(personality_mixer.base_personalities),
            "anchor_technology": "operational",
            "version": ANCHORLAB_VERSION,
            "uptime_status": "running"
        }
        
    except Exception as e:
        return {"error": f"Analytics failed: {str(e)}"}

@app.get("/api/admin/cleanup_stats")
async def cleanup_stats():
    """Get session storage statistics"""
    try:
        session_keys = await redis_client.keys("anchorlab:session:*")
        meta_keys = await redis_client.keys("anchorlab:meta:*")
        session_count = len(session_keys)
        
        return {
            "active_sessions": session_count,
            "metadata_entries": len(meta_keys),
            "cleanup_after_days": CLEANUP_AFTER_DAYS,
            "next_cleanup_hours": CLEANUP_INTERVAL_HOURS,
            "redis_connected": True
        }
    except Exception as e:
        return {"error": f"Stats failed: {str(e)}"}

@app.post("/api/admin/manual_cleanup")
async def manual_cleanup():
    """Manually trigger session cleanup"""
    try:
        cleaned = await cleanup_abandoned_sessions()
        return {"message": f"Cleaned {cleaned} abandoned sessions"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual cleanup failed: {str(e)}")

# ---------- Error Handlers ---------- #
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url),
        "service": "AnchorLab.ai"
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "status_code": 500,
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url),
        "service": "AnchorLab.ai"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "anchorlab_main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    )