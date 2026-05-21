"""
main.py — FastAPI Application (Fixed).

Key fixes:
- /confirm-book-event now ACTUALLY creates the Google Calendar event
  (calendar_agent no longer calls create_event tool — it just builds the card)
- /confirm-send-email actually sends via Gmail (unchanged, already correct)
- Added google_credentials_api_key dependency for the actual event creation
"""
import uuid
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from agents.orchestrator import HROrchestratorGraph
from memory.session_store import init_db, save_message, get_history, get_all_sessions, clear_session
from mcp_tools.gmail_tools import send_email
from mcp_tools.calendar_tools import _get_calendar_service   # reuse the helper


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting HR Agent API...")
    init_db()
    print("✅ SQLite initialized")
    app.state.orchestrator = HROrchestratorGraph()
    print("✅ LangGraph orchestrator ready")
    print(f"✅ API running at http://{settings.backend_host}:{settings.backend_port}")
    print("📚 Docs: http://localhost:8000/docs")
    yield
    print("👋 Shutting down HR Agent API")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI HR Assistant API",
    description="Multi-agent HR assistant with RAG + Calendar + Email",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    agent: str
    intent: str
    sources: list = []
    action_card: dict | None = None


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str


class BookEventRequest(BaseModel):
    """
    Sent from the React UI when user clicks Create Event.
    The UI may have edited the fields before submitting.
    """
    title: str
    date: str            # YYYY-MM-DD
    start_time: str      # HH:MM
    duration_minutes: int = 30
    attendee_email: Optional[str] = None
    description: Optional[str] = ""


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "HR Agent API", "version": "1.1.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = request.session_id or str(uuid.uuid4())
    save_message(session_id, "user", request.message)

    try:
        orchestrator: HROrchestratorGraph = app.state.orchestrator
        result = orchestrator.run(session_id, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

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
    messages = get_history(session_id, limit=limit)
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@app.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    clear_session(session_id)
    return {"message": f"Session {session_id} cleared."}


@app.get("/sessions")
async def list_sessions():
    sessions = get_all_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@app.post("/confirm-send-email")
async def confirm_send_email(request: SendEmailRequest):
    """
    Actually send the email via Gmail API after user clicks Send in the UI.
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
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Send failed"),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/confirm-book-event")
async def confirm_book_event(request: BookEventRequest):
    """
    Actually create the Google Calendar event after user clicks Create in UI.
    Accepts the (possibly edited) event data from the React UI.
    """
    try:
        service = _get_calendar_service()

        start_dt = datetime.strptime(
            f"{request.date} {request.start_time}", "%Y-%m-%d %H:%M"
        )
        end_dt = start_dt + timedelta(minutes=request.duration_minutes)

        event_body = {
            "summary": request.title,
            "description": request.description or "",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
        }

        if request.attendee_email and request.attendee_email.strip():
            event_body["attendees"] = [{"email": request.attendee_email.strip()}]

        event = service.events().insert(
            calendarId="primary",
            body=event_body,
            sendUpdates="all" if request.attendee_email else "none",
        ).execute()

        return {
            "success": True,
            "event_id": event["id"],
            "html_link": event.get("htmlLink", ""),
            "message": f"Event '{request.title}' created in Google Calendar.",
            "title": request.title,
            "date": request.date,
            "start_time": request.start_time,
            "duration_minutes": request.duration_minutes,
            "attendee_email": request.attendee_email or "",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )