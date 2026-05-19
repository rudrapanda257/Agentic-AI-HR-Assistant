"""
calendar_tools.py — Google Calendar tools for the Calendar Agent.

Tools available:
    - list_events(days_ahead)         → list upcoming events
    - create_event(title, date, time, duration_min, attendee_email)
    - delete_event(event_id)

These are standard Python functions wrapped as LangChain @tool.
The Calendar Agent can call any of them based on user intent.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from langchain_core.tools import tool

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_calendar_service():
    """Load saved credentials and build the Calendar API service."""
    token_path = Path(settings.google_token_path)

    if not token_path.exists():
        raise FileNotFoundError(
            "token.json not found. Run: python google_credentials/auth_setup.py"
        )

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


@tool
def list_events(days_ahead: int = 7) -> str:
    """
    List upcoming Google Calendar events.
    
    Args:
        days_ahead: How many days ahead to look (default: 7)
    
    Returns:
        JSON string with list of events including id, title, start, end, attendees
    """
    try:
        service = _get_calendar_service()

        now = datetime.utcnow().isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                timeMax=end_time,
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            return json.dumps({"events": [], "message": f"No events in the next {days_ahead} days."})

        formatted = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            attendees = [a["email"] for a in event.get("attendees", [])]

            formatted.append({
                "id": event["id"],
                "title": event.get("summary", "No title"),
                "start": start,
                "end": end,
                "attendees": attendees,
                "meet_link": event.get("hangoutLink", ""),
            })

        return json.dumps({"events": formatted, "count": len(formatted)})

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def create_event(
    title: str,
    date: str,
    start_time: str,
    duration_minutes: int = 30,
    attendee_email: Optional[str] = None,
    description: str = "",
) -> str:
    """
    Create a new Google Calendar event.
    
    Args:
        title: Event title (e.g. "1:1 with Priya")
        date: Date in YYYY-MM-DD format (e.g. "2026-05-21")
        start_time: Time in HH:MM format, 24h (e.g. "15:00")
        duration_minutes: Duration in minutes (default: 30)
        attendee_email: Email to invite (optional)
        description: Event description (optional)
    
    Returns:
        JSON string with created event details including event_id
    """
    try:
        service = _get_calendar_service()

        # Parse start datetime
        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # Build event body
        event_body = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Kolkata",  # IST — change if needed
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
        }

        if attendee_email:
            event_body["attendees"] = [{"email": attendee_email}]

        event = service.events().insert(
            calendarId="primary",
            body=event_body,
            sendUpdates="all" if attendee_email else "none",
        ).execute()

        return json.dumps({
            "success": True,
            "event_id": event["id"],
            "title": event.get("summary"),
            "start": event["start"].get("dateTime"),
            "end": event["end"].get("dateTime"),
            "html_link": event.get("htmlLink", ""),
            "message": f"Event '{title}' created successfully.",
        })

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
def delete_event(event_id: str) -> str:
    """
    Delete a Google Calendar event by its event ID.
    
    Args:
        event_id: The Google Calendar event ID (get from list_events)
    
    Returns:
        JSON string confirming deletion
    """
    try:
        service = _get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()

        return json.dumps({
            "success": True,
            "message": f"Event {event_id} deleted successfully.",
        })

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# All tools as a list — import this in calendar_agent.py
CALENDAR_TOOLS = [list_events, create_event, delete_event]


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Calendar tools...")
    result = list_events.invoke({"days_ahead": 7})
    print(json.loads(result))