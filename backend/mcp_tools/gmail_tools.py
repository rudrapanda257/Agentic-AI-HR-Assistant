"""
gmail_tools.py — Gmail tools for the Email Agent.

Tools available:
    - list_emails(max_results)          → list recent inbox emails
    - draft_email(to, subject, body)    → creates a draft (does NOT send)
    - send_email(to, subject, body)     → sends immediately

⚠️  SAFETY: The agent NEVER calls send_email directly.
    It always calls draft_email first, shows the user a preview card,
    and only sends after the user clicks "Send" in the React UI,
    which calls the /confirm-send-email FastAPI endpoint.
"""
import sys
import json
import base64
from pathlib import Path
from email.mime.text import MIMEText
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from langchain_core.tools import tool

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


def _get_gmail_service():
    """Load saved credentials and build the Gmail API service."""
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

    return build("gmail", "v1", credentials=creds)


def _build_mime_message(to: str, subject: str, body: str) -> str:
    """Build a base64-encoded MIME email."""
    message = MIMEText(body, "plain")
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return raw


@tool
def list_emails(max_results: int = 5) -> str:
    """
    List recent emails from Gmail inbox.
    
    Args:
        max_results: Number of emails to return (default: 5)
    
    Returns:
        JSON string with list of emails (id, from, subject, snippet, date)
    """
    try:
        service = _get_gmail_service()

        results = (
            service.users()
            .messages()
            .list(userId="me", maxResults=max_results, labelIds=["INBOX"])
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            return json.dumps({"emails": [], "message": "No emails found."})

        emails = []
        for msg_ref in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="metadata",
                     metadataHeaders=["From", "Subject", "Date"])
                .execute()
            )

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            emails.append({
                "id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })

        return json.dumps({"emails": emails, "count": len(emails)})

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def draft_email(to: str, subject: str, body: str) -> str:
    """
    Compose an email draft. Does NOT send — user must confirm in UI.
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Full email body text
    
    Returns:
        JSON string with draft details for display in the React confirmation card
    """
    # We do NOT call Gmail API here — we just return the draft for UI confirmation
    # The actual send happens via /confirm-send-email endpoint after user clicks Send
    return json.dumps({
        "action": "draft_ready",
        "to": to,
        "subject": subject,
        "body": body,
        "message": "Draft ready. Waiting for user confirmation before sending.",
    })


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email via Gmail. Only call this after user has confirmed the draft.
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Full email body text
    
    Returns:
        JSON string confirming send
    """
    try:
        service = _get_gmail_service()

        raw = _build_mime_message(to, subject, body)
        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )

        return json.dumps({
            "success": True,
            "message_id": sent["id"],
            "message": f"Email sent to {to} successfully.",
        })

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# All tools — import this in email_agent.py
GMAIL_TOOLS = [list_emails, draft_email, send_email]


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Gmail list_emails tool...")
    result = list_emails.invoke({"max_results": 3})
    data = json.loads(result)
    if "error" in data:
        print("Error:", data["error"])
    else:
        print(f"Found {data['count']} emails:")
        for email in data["emails"]:
            print(f"  From: {email['from']}")
            print(f"  Subject: {email['subject']}")
            print()