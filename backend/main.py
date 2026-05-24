"""
main.py

This file is the main FastAPI backend server.

Main Responsibilities:
1. Start FastAPI server
2. Handle chat requests
3. Connect LangGraph orchestrator
4. Store chat history in SQLite
5. Send Gmail emails
6. Create Google Calendar events
7. Provide API endpoints for frontend

Architecture:
Frontend React UI
        ↓
FastAPI Backend (main.py)
        ↓
LangGraph Orchestrator
        ↓
Policy Agent / Calendar Agent / Email Agent
        ↓
Google APIs + ChromaDB + Gemini
"""

# ─────────────────────────────────────────────────────────
# IMPORT SECTION
# This block imports all required libraries
# ─────────────────────────────────────────────────────────

# Used to generate unique session IDs
import uuid

# Used for JSON handling
import json

# Used for FastAPI app lifecycle management
from contextlib import asynccontextmanager

# Used for date/time calculations
from datetime import datetime, timedelta

# Used for optional field typing
from typing import Optional


# FastAPI framework
from fastapi import FastAPI, HTTPException


# Enables frontend-backend communication
from fastapi.middleware.cors import CORSMiddleware


# Used for request/response validation
from pydantic import BaseModel


# Import application settings
from config import settings


# Import LangGraph orchestrator
from agents.orchestrator import HROrchestratorGraph


# Import SQLite memory functions
from memory.session_store import (
    init_db,
    save_message,
    get_history,
    get_all_sessions,
    clear_session
)


# ─────────────────────────────────────────────────────────
# APP LIFECYCLE BLOCK
# Runs when FastAPI server starts/stops
# ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):

    """
    Startup + shutdown lifecycle manager.
    """

    # Print startup message
    print("🚀 Starting HR Agent API...")


    # Initialize SQLite database
    init_db()


    # Print DB success message
    print("✅ SQLite initialized")


    # Create LangGraph orchestrator object
    app.state.orchestrator = HROrchestratorGraph()


    # Print orchestrator status
    print("✅ LangGraph orchestrator ready")


    # Print backend server URL
    print(
        f"✅ API running at "
        f"http://{settings.backend_host}:{settings.backend_port}"
    )


    # Print Swagger docs URL
    print("📚 Docs: http://localhost:8000/docs")


    # Allow app execution
    yield


    # Shutdown message
    print("👋 Shutting down HR Agent API")


# ─────────────────────────────────────────────────────────
# FASTAPI APP CREATION BLOCK
# Creates backend server object
# ─────────────────────────────────────────────────────────

app = FastAPI(

    # API title
    title="AI HR Assistant API",

    # API description
    description="Multi-agent HR assistant with RAG + Calendar + Email",

    # API version
    version="2.0.0",

    # Startup/shutdown manager
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────
# CORS CONFIGURATION BLOCK
# Allows frontend React app to access backend
# ─────────────────────────────────────────────────────────

app.add_middleware(

    # Enable CORS middleware
    CORSMiddleware,

    # Allowed frontend URLs
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],

    # Allow cookies/authentication
    allow_credentials=True,

    # Allow all HTTP methods
    allow_methods=["*"],

    # Allow all request headers
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────
# PYDANTIC REQUEST/RESPONSE MODELS
# Defines API request body structures
# ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):

    """
    Request structure for /chat API.
    """

    # Optional session ID
    session_id: str | None = None

    # User message
    message: str


class ChatResponse(BaseModel):

    """
    Response structure returned by /chat API.
    """

    # Chat session ID
    session_id: str

    # AI generated answer
    answer: str

    # Which agent handled request
    agent: str

    # Detected intent
    intent: str

    # Retrieved document sources
    sources: list = []

    # Optional frontend action card
    action_card: dict | None = None


class SendEmailRequest(BaseModel):

    """
    Request structure for email sending.
    """

    # Receiver email
    to: str

    # Email subject
    subject: str

    # Email body
    body: str


class BookEventRequest(BaseModel):

    """
    Request structure for calendar event creation.
    """

    # Event title
    title: str

    # Event date
    date: str

    # Event start time
    start_time: str

    # Event duration
    duration_minutes: int = 30

    # Optional attendee email
    attendee_email: Optional[str] = None

    # Optional event description
    description: Optional[str] = ""


# ─────────────────────────────────────────────────────────
# HEALTH CHECK API
# Used to check if backend server is alive
# ─────────────────────────────────────────────────────────

@app.get("/health")

async def health_check():

    """
    Simple server health check endpoint.
    """

    return {

        # Backend status
        "status": "ok",

        # Service name
        "service": "HR Agent API",

        # API version
        "version": "2.0.0"
    }


# ─────────────────────────────────────────────────────────
# MAIN CHAT API
# Handles user chat requests
# ─────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)

async def chat(request: ChatRequest):

    """
    Main AI chat endpoint.
    """

    # Check if user message is empty
    if not request.message.strip():

        # Return HTTP 400 error
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )


    # Create session ID if missing
    session_id = request.session_id or str(uuid.uuid4())


    # Save user message into SQLite memory
    save_message(
        session_id,
        "user",
        request.message
    )


    try:

        # Load orchestrator object
        orchestrator: HROrchestratorGraph = app.state.orchestrator


        # Run LangGraph workflow
        result = orchestrator.run(
            session_id,
            request.message
        )

    except Exception as e:

        # Return AI processing error
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


    # Save assistant response into SQLite
    save_message(

        # Session ID
        session_id,

        # Message role
        "assistant",

        # AI response text
        result["answer"],

        # Agent name
        agent=result["agent"],

        # Extra metadata
        metadata={

            # Document sources
            "sources": result.get("sources", []),

            # UI action card
            "action_card": result.get("action_card"),
        },
    )


    # Return final API response
    return ChatResponse(

        session_id=session_id,
        answer=result["answer"],
        agent=result["agent"],
        intent=result["intent"],
        sources=result.get("sources", []),
        action_card=result.get("action_card"),
    )


# ─────────────────────────────────────────────────────────
# CHAT HISTORY APIs
# Handles session history management
# ─────────────────────────────────────────────────────────

@app.get("/history/{session_id}")

async def get_chat_history(session_id: str, limit: int = 50):

    """
    Return previous chat messages from SQLite.
    """

    # Load messages from DB
    messages = get_history(session_id, limit=limit)


    # Return chat history
    return {

        "session_id": session_id,
        "messages": messages,
        "count": len(messages)
    }


@app.delete("/history/{session_id}")

async def clear_chat_history(session_id: str):

    """
    Delete session chat history.
    """

    # Remove session messages
    clear_session(session_id)


    # Return success message
    return {
        "message": f"Session {session_id} cleared."
    }


@app.get("/sessions")

async def list_sessions():

    """
    Return all stored chat sessions.
    """

    # Get all sessions
    sessions = get_all_sessions()


    # Return session list
    return {

        "sessions": sessions,
        "count": len(sessions)
    }


# ─────────────────────────────────────────────────────────
# EMAIL API
# Sends real Gmail emails
# ─────────────────────────────────────────────────────────

@app.post("/confirm-send-email")

async def confirm_send_email(request: SendEmailRequest):

    """
    Send real email using Gmail API.
    Called when user clicks Send button.
    """

    # Import email-related libraries
    import base64
    from email.mime.text import MIMEText
    from pathlib import Path
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build


    # Gmail OAuth scopes
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    try:

        # Load token.json path
        token_path = Path(settings.google_token_path)


        # Check token existence
        if not token_path.exists():

            raise HTTPException(
                status_code=500,
                detail="Google token not found."
            )


        # Load Google OAuth credentials
        creds = Credentials.from_authorized_user_file(
            str(token_path),
            GMAIL_SCOPES
        )


        # Refresh expired token automatically
        if creds.expired and creds.refresh_token:

            creds.refresh(Request())

            with open(token_path, "w") as f:
                f.write(creds.to_json())


        # Create Gmail API service
        service = build(
            "gmail",
            "v1",
            credentials=creds
        )


        # Create MIME email message
        message = MIMEText(
            request.body,
            "plain"
        )


        # Add receiver email
        message["to"] = request.to


        # Add email subject
        message["subject"] = request.subject


        # Convert email into base64 encoded format
        raw = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()


        # Send Gmail message
        sent = service.users().messages().send(

            # Current logged-in user
            userId="me",

            # Encoded email body
            body={"raw": raw}

        ).execute()


        # Print success log
        print(f"✅ Email sent to {request.to}")


        # Return success response
        return {

            "success": True,
            "message_id": sent["id"],
            "message": f"Email sent successfully."
        }

    except Exception as e:

        # Print error log
        print(f"❌ Email send failed: {e}")


        # Return HTTP error
        raise HTTPException(
            status_code=500,
            detail=f"Gmail send failed: {str(e)}"
        )


# ─────────────────────────────────────────────────────────
# CALENDAR EVENT API
# Creates real Google Calendar events
# ─────────────────────────────────────────────────────────

@app.post("/confirm-book-event")

async def confirm_book_event(request: BookEventRequest):

    """
    Create real Google Calendar event.
    """

    # Google Calendar API imports
    from pathlib import Path
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build


    # Google Calendar OAuth scope
    CALENDAR_SCOPES = [
        "https://www.googleapis.com/auth/calendar"
    ]

    try:

        # Load token.json
        token_path = Path(settings.google_token_path)


        # Ensure token exists
        if not token_path.exists():

            raise HTTPException(
                status_code=500,
                detail="Google token not found."
            )


        # Load credentials
        creds = Credentials.from_authorized_user_file(
            str(token_path),
            CALENDAR_SCOPES
        )


        # Refresh expired token
        if creds.expired and creds.refresh_token:

            creds.refresh(Request())

            with open(token_path, "w") as f:
                f.write(creds.to_json())


        # Create Calendar API service
        service = build(
            "calendar",
            "v3",
            credentials=creds
        )


        # Convert request date/time into datetime object
        start_dt = datetime.strptime(

            f"{request.date} {request.start_time}",
            "%Y-%m-%d %H:%M"
        )


        # Calculate event end time
        end_dt = start_dt + timedelta(
            minutes=request.duration_minutes
        )


        # Build calendar event JSON body
        event_body = {

            # Event title
            "summary": request.title,

            # Event description
            "description": request.description or "",

            # Event start details
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Kolkata",
            },

            # Event end details
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
        }


        # Add attendee email if provided
        email = (request.attendee_email or "").strip()

        if email and "@" in email:

            event_body["attendees"] = [
                {"email": email}
            ]


        # Create Google Calendar event
        event = service.events().insert(

            # Use primary calendar
            calendarId="primary",

            # Event JSON body
            body=event_body,

            # Send calendar invitations
            sendUpdates="all" if email else "none",

        ).execute()


        # Print success log
        print(f"✅ Calendar event created")


        # Return success response
        return {

            "success": True,
            "event_id": event["id"],
            "html_link": event.get("htmlLink", ""),
            "message": f"Event created successfully.",
        }

    except Exception as e:

        # Print error log
        print(f"❌ Calendar create failed: {e}")


        # Return HTTP error
        raise HTTPException(
            status_code=500,
            detail=f"Calendar error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────
# SERVER STARTUP BLOCK
# Runs backend server locally
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Import Uvicorn ASGI server
    import uvicorn


    # Start FastAPI server
    uvicorn.run(

        # Main FastAPI app
        "main:app",

        # Backend host
        host=settings.backend_host,

        # Backend port
        port=settings.backend_port,

        # Auto-reload on code changes
        reload=True,
    )