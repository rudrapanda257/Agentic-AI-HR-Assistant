"""
calendar_tools.py — FIXED: create_event is now DRY-RUN mode.

ROOT CAUSE FIX:
Previously create_event called Google Calendar API immediately when the agent ran.
Then CalendarCard.jsx also called /confirm-book-event which tried to create AGAIN.
Result: either duplicate events or the UI button had no real effect.

FIX: create_event tool now returns the event data WITHOUT calling Google API.
The REAL calendar creation happens only in /confirm-book-event endpoint
when the user clicks Create in the React UI.

This means: agent parses the request → builds action_card → user reviews/edits →
clicks Create → /confirm-book-event → Google Calendar API called ONCE.

list_events and delete_event still call the API normally.
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
    """Load saved credentials and build Calendar API service."""
    token_path = Path(settings.google_token_path)
    if not token_path.exists():
        raise FileNotFoundError(
            "token.json not found. Run: python google_credentials/auth_setup.py"
        )
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
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
        JSON string with list of events
    """
    try:
        service = _get_calendar_service()
        now = datetime.utcnow().isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=end_time,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

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
    Prepare a Google Calendar event for review. Does NOT create immediately.
    User must click Create in the UI to actually add to Google Calendar.

    Args:
        title: Event title (e.g. "1:1 with Priya")
        date: Date in YYYY-MM-DD format (e.g. "2026-05-21")
        start_time: Time in HH:MM 24h format (e.g. "15:00")
        duration_minutes: Duration in minutes (default: 30)
        attendee_email: Email to invite (optional)
        description: Event description (optional)

    Returns:
        JSON with event details for UI review card (no Google API call yet)
    """
    # ── DRY-RUN: validate inputs, return data for UI review ──────────────────
    # The REAL Google Calendar API call happens in /confirm-book-event endpoint
    # when user clicks Create button in CalendarCard.jsx
    try:
        # Validate date/time format so we catch errors early
        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        return json.dumps({
            "success": True,
            "dry_run": True,
            "title": title,
            "date": date,
            "start_time": start_time,
            "end_time": end_dt.strftime("%H:%M"),
            "duration_minutes": duration_minutes,
            "attendee_email": attendee_email or "",
            "description": description,
            "message": f"Event '{title}' ready for review. Click Create to add to Google Calendar.",
        })

    except ValueError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid date/time format: {e}. Use YYYY-MM-DD for date and HH:MM for time."
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


CALENDAR_TOOLS = [list_events, create_event, delete_event]


if __name__ == "__main__":
    print("Testing list_events...")
    result = list_events.invoke({"days_ahead": 7})
    data = json.loads(result)
    if "error" in data:
        print("Error:", data["error"])
    else:
        print(f"Found {data['count']} events:")
        for e in data["events"]:
            print(f"  {e['title']} @ {e['start']}")