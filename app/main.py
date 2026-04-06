"""
╔══════════════════════════════════════════════════════╗
║   🦊 Fennec RAG — Customer Support Backend          ║
║   FastAPI + Conversational RAG + Semantic Routing   ║
╚══════════════════════════════════════════════════════╝
"""

import os
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .rag_engine import CustomerSupportRAG
from .models import ChatRequest, ChatResponse, SessionInfo, HealthCheck

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("customer_support")

# ── Global RAG Engine ─────────────────────────────────────────────────────────
rag_engine: Optional[CustomerSupportRAG] = None
sessions: dict = {}  # session_id → metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG engine on startup, cleanup on shutdown."""
    global rag_engine
    logger.info("🚀 Initializing Fennec RAG Customer Support Engine...")
    try:
        rag_engine = CustomerSupportRAG()
        await rag_engine.initialize()
        logger.info("✅ RAG engine ready — knowledge base loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG engine: {e}")
        raise
    yield
    logger.info("🛑 Shutting down customer support engine...")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="🦊 Fennec Customer Support API",
    description="Intelligent customer support powered by Fennec RAG framework",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    index = os.path.join(frontend_path, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return JSONResponse({"message": "🦊 Fennec Customer Support API", "docs": "/docs"})


@app.get("/health", response_model=HealthCheck, tags=["System"])
async def health_check():
    """Check system health and knowledge base status."""
    return HealthCheck(
        status="healthy",
        engine_ready=rag_engine is not None and rag_engine.is_ready,
        active_sessions=len(sessions),
        knowledge_base_docs=rag_engine.doc_count if rag_engine else 0,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/session/new", tags=["Session"])
async def new_session(user_name: Optional[str] = None):
    """Start a new support conversation session."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "user_name": user_name or "Guest",
        "created_at": datetime.utcnow().isoformat(),
        "message_count": 0,
    }
    rag_engine.create_session(session_id)
    logger.info(f"📝 New session: {session_id} | User: {user_name or 'Guest'}")
    return SessionInfo(
        session_id=session_id,
        user_name=user_name or "Guest",
        message="Session started! How can I help you today?",
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Send a message and get an intelligent response.

    The engine automatically:
    - Routes your query (FAQ / complaints / technical / orders / general)
    - Retrieves relevant knowledge base documents
    - Guards against hallucination
    - Remembers conversation history within the session
    """
    if not rag_engine or not rag_engine.is_ready:
        raise HTTPException(status_code=503, detail="RAG engine not ready yet")

    session_id = request.session_id
    if session_id not in sessions:
        # Auto-create session if missing
        sessions[session_id] = {
            "id": session_id,
            "user_name": "Guest",
            "created_at": datetime.utcnow().isoformat(),
            "message_count": 0,
        }
        rag_engine.create_session(session_id)

    sessions[session_id]["message_count"] += 1

    try:
        result = await rag_engine.answer(
            query=request.message,
            session_id=session_id,
            language=request.language or "auto",
        )
        logger.info(
            f"💬 [{session_id[:8]}] route={result.route} "
            f"confidence={result.confidence:.2f} | Q: {request.message[:60]}"
        )
        return ChatResponse(
            session_id=session_id,
            message=result.answer,
            route=result.route,
            confidence=result.confidence,
            sources=result.sources,
            suggestions=result.suggestions,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"❌ Chat error [{session_id}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}", tags=["Session"])
async def end_session(session_id: str):
    """End a session and free its memory."""
    if session_id in sessions:
        sessions.pop(session_id)
        rag_engine.remove_session(session_id)
        return {"message": "Session ended", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions", tags=["Admin"])
async def list_sessions():
    """List all active sessions (admin view)."""
    return {"active_sessions": len(sessions), "sessions": list(sessions.values())}


@app.post("/knowledge-base/reload", tags=["Admin"])
async def reload_knowledge_base():
    """Reload the knowledge base from disk."""
    if not rag_engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    doc_count = await rag_engine.reload_knowledge_base()
    return {"message": "Knowledge base reloaded", "documents_loaded": doc_count}


@app.get("/stats", tags=["Admin"])
async def get_stats():
    """Get engine statistics."""
    if not rag_engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    return rag_engine.get_stats()
