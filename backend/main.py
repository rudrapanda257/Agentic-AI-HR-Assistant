"""
main.py — FastAPI Application.

Endpoints:
    GET  /health                    → health check
    POST /chat                      → main chat endpoint
    GET  /history/{session_id}      → get chat history
    POST /confirm-send-email        → actually send the email after user confirms
    POST /confirm-book-event        → confirm already-created calendar event (noop)
    DELETE /history/{session_id}    → clear session history

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Docs at: http://localhost:8000/docs
"""
import uuid
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Internal imports ──────────────────────────────────────────────────────────
from config import settings
from agents.orchestrator import HROrchestratorGraph
from memory.session_store import init_db, save_message, get_history, get_all_sessions, clear_session
from mcp_tools.gmail_tools import send_email


# ── Lifespan (startup/shutdown) ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    print("🚀 Starting HR Agent API...")

    # Init SQLite
    init_db()
    print("✅ SQLite initialized")

    # Init orchestrator (loads all models + agents)
    app.state.orchestrator = HROrchestratorGraph()
    print("✅ LangGraph orchestrator ready")

    print(f"✅ API running at http://{settings.backend_host}:{settings.backend_port}")
    print("📚 Docs: http://localhost:8000/docs")
    print("🔍 LangSmith: https://smith.langchain.com")
    print()

    yield  # App is running

    print("👋 Shutting down HR Agent API")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI HR Assistant API",
    description="Multi-agent HR assistant with RAG + Calendar + Email",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React frontend (localhost:5173) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA dev server (if used)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str | None = None   # auto-generated if not provided
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "user_123",
                "message": "How many casual leaves do I get?"
            }
        }


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    agent: str               # "policy" | "calendar" | "email"
    intent: str
    sources: list = []       # citation chips for policy answers
    action_card: dict | None = None   # confirmation card for calendar/email


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str

    class Config:
        json_schema_extra = {
            "example": {
                "to": "manager@company.com",
                "subject": "WFH Request — Friday",
                "body": "Hi, I'd like to request WFH on Friday..."
            }
        }


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Quick health check — use this to verify the API is running."""
    return {
        "status": "ok",
        "service": "HR Agent API",
        "version": "1.0.0",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    
    Send a message, get back an answer from the appropriate agent.
    session_id is auto-generated if not provided — return it to the client
    and include it in subsequent requests to maintain conversation context.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    # Save user message
    save_message(session_id, "user", request.message)

    # Run orchestrator
    try:
        orchestrator: HROrchestratorGraph = app.state.orchestrator
        result = orchestrator.run(session_id, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Save assistant response
    save_message(
        session_id,
        "assistant",
        result["answer"],
        agent=result["agent"],
        metadata={
            "sources": result.get("sources", []),
            "action_card": result.get("action_card"),
        },
    )

    return ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        agent=result["agent"],
        intent=result["intent"],
        sources=result.get("sources", []),
        action_card=result.get("action_card"),
    )


@app.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session."""
    messages = get_history(session_id, limit=limit)
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@app.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear all messages for a session (start fresh)."""
    clear_session(session_id)
    return {"message": f"Session {session_id} cleared."}


@app.get("/sessions")
async def list_sessions():
    """Admin: list all chat sessions."""
    sessions = get_all_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@app.post("/confirm-send-email")
async def confirm_send_email(request: SendEmailRequest):
    """
    Actually send an email after user confirms in the React UI.
    
    The email agent only drafts — this endpoint does the actual send.
    This is the ONLY place where send_email tool is called for real.
    """
    try:
        result_json = send_email.invoke({
            "to": request.to,
            "subject": request.subject,
            "body": request.body,
        })
        result = json.loads(result_json)

        if result.get("success"):
            return {"success": True, "message": f"Email sent to {request.to}"}
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Send failed"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/confirm-book-event")
async def confirm_book_event(event_data: dict):
    """
    Acknowledge calendar event booking.
    
    The calendar agent already books the event immediately via create_event tool.
    This endpoint exists so the React UI can show a "booked" confirmation state.
    """
    return {"success": True, "message": "Event confirmed.", "event": event_data}


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )