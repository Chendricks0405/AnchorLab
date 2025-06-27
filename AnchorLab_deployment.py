# perceptia_main.py
"""
Perceptia.io - AI Personality Marketplace API
=============================================
Dedicated Render deployment for personality generation and mixing
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

# Import our enhanced systems
from enhanced_anchor_system import EnhancedAnchorSession
from memory_system_implementation import EnhancedMemorySystem
from personality_mixer import PersonalityMixer

load_dotenv()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
PERCEPTIA_VERSION = "1.0.0"

# Initialize FastAPI with metadata
app = FastAPI(
    title="Perceptia.io API",
    description="AI Personality Marketplace - Create, Mix, and Deploy Scientific AI Personalities",
    version=PERCEPTIA_VERSION,
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

class MixRequest(BaseModel):
    combinations: List[tuple]  # [(personality_name, weight), ...]
    custom_goal: Optional[str] = None

class SessionRequest(BaseModel):
    session_id: str
    personality_seed: Optional[str] = None
    user_input: Optional[str] = None

# ---------- Startup/Shutdown ---------- #
@app.on_event("startup")
async def startup_event():
    """Initialize Perceptia systems"""
    try:
        # Test Redis connection
        await redis_client.ping()
        print("✓ Redis connected")
        
        # Load personality foundations
        personality_mixer.load_foundation_personalities()
        print("✓ Foundation personalities loaded")
        
        # Start background tasks
        asyncio.create_task(cleanup_expired_sessions())
        print("✓ Background cleanup started")
        
        print(f"🚀 Perceptia.io v{PERCEPTIA_VERSION} started successfully")
        
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await redis_client.close()
    print("👋 Perceptia.io shutdown complete")

# ---------- Core Routes ---------- #
@app.get("/")
async def root():
    """Health check and system info"""
    return {
        "service": "Perceptia.io",
        "version": PERCEPTIA_VERSION,
        "description": "AI Personality Marketplace",
        "status": "operational",
        "features": [
            "Scientific personality generation",
            "Big 5 + Moral Foundations integration", 
            "Personality mixing engine",
            "Enhanced anchor system",
            "Memory persistence",
            "Session management"
        ],
        "endpoints": {
            "personalities": "/api/personalities",
            "mixer": "/api/mix",
            "sessions": "/api/sessions",
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
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "redis": "connected" if redis_ping else "disconnected",
            "foundation_personalities": foundation_count,
            "version": PERCEPTIA_VERSION
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
            "personality_traits": config.get("personality_vector", {})
        }
    
    return {
        "personalities": personalities,
        "count": len(personalities),
        "mixing_combinations": f"{len(personalities) * (len(personalities) - 1)} possible pairs"
    }

@app.post("/api/personalities/generate")
async def generate_personality(request: PersonalityRequest):
    """Generate a custom personality seed"""
    try:
        # Create enhanced anchor session with custom personality
        session = EnhancedAnchorSession(persona=request.name)
        
        # Apply Big 5 scores to anchor vector
        if request.big5_scores:
            # Map Big 5 to anchor vector (simplified mapping)
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
            "memory_scaffolding": {"root_nodes": [f"CUST_{request.name[:3].upper()}001"]},
            "constraints": {"reply_hygiene": f"Embody {request.name} personality traits."}
        }
        
        return {
            "success": True,
            "personality_seed": personality_seed,
            "anchor_diagnostics": session.export_view()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Generation failed: {str(e)}")

@app.post("/api/personalities/mix")
async def mix_personalities(request: MixRequest):
    """Mix multiple foundation personalities"""
    try:
        mixed_personality = personality_mixer.mix_personalities(
            combinations=request.combinations,
            custom_goal=request.custom_goal
        )
        
        return {
            "success": True,
            "mixed_personality": mixed_personality,
            "source_combinations": request.combinations
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mixing failed: {str(e)}")

# ---------- Session Management ---------- #
@app.post("/api/sessions/create")
async def create_session(request: SessionRequest):
    """Create new anchor session with personality"""
    try:
        session_id = request.session_id
        
        # Create enhanced session with memory
        session = EnhancedAnchorSession(persona=request.personality_seed)
        memory_system = EnhancedMemorySystem()
        
        # Store session in Redis
        session_data = {
            "session": session.export_view(),
            "memory_stats": memory_system.get_memory_stats(),
            "created_at": datetime.now().isoformat(),
            "personality_seed": request.personality_seed
        }
        
        await redis_client.set(
            f"perceptia:session:{session_id}",
            json.dumps(session_data),
            ex=60 * 60 * 24 * 7  # 7 day TTL
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "session_data": session_data,
            "expires_in": "7 days"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Session creation failed: {str(e)}")

@app.post("/api/sessions/{session_id}/interact")
async def interact_with_session(session_id: str, request: SessionRequest):
    """Interact with an existing session"""
    try:
        # Retrieve session
        session_data = await redis_client.get(f"perceptia:session:{session_id}")
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_info = json.loads(session_data)
        
        # Process interaction (simplified)
        response = {
            "session_id": session_id,
            "user_input": request.user_input,
            "ai_response": f"Processing: {request.user_input}",
            "anchor_state": session_info["session"]["anchor_vector"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Update session timestamp
        session_info["last_interaction"] = datetime.now().isoformat()
        await redis_client.set(
            f"perceptia:session:{session_id}",
            json.dumps(session_info),
            ex=60 * 60 * 24 * 7
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interaction failed: {str(e)}")

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    try:
        session_data = await redis_client.get(f"perceptia:session:{session_id}")
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return json.loads(session_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session retrieval failed: {str(e)}")

# ---------- Analytics & Management ---------- #
@app.get("/api/analytics/overview")
async def get_analytics():
    """Get system analytics"""
    try:
        # Get all session keys
        session_keys = await redis_client.keys("perceptia:session:*")
        
        # Basic analytics
        active_sessions = len(session_keys)
        personality_usage = {}
        
        for key in session_keys[:100]:  # Sample first 100
            session_data = await redis_client.get(key)
            if session_data:
                data = json.loads(session_data)
                personality = data.get("personality_seed", "unknown")
                personality_usage[personality] = personality_usage.get(personality, 0) + 1
        
        return {
            "active_sessions": active_sessions,
            "personality_usage": personality_usage,
            "foundation_personalities": len(personality_mixer.base_personalities),
            "system_uptime": "tracking...",
            "version": PERCEPTIA_VERSION
        }
        
    except Exception as e:
        return {"error": f"Analytics failed: {str(e)}"}

# ---------- Background Tasks ---------- #
async def cleanup_expired_sessions():
    """Background task to cleanup expired sessions"""
    while True:
        try:
            # This would normally be handled by Redis TTL, but we can add custom cleanup
            session_keys = await redis_client.keys("perceptia:session:*")
            print(f"🧹 Session cleanup check: {len(session_keys)} active sessions")
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            await asyncio.sleep(300)  # Retry in 5 minutes

# ---------- Error Handlers ---------- #
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url)
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "status_code": 500,
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "perceptia_main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    )