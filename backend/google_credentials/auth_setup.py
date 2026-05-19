"""
auth_setup.py — ONE-TIME Google OAuth setup.

Run this ONCE to generate token.json:
    cd backend && python google_credentials/auth_setup.py

What it does:
    1. Opens a browser with Google login
    2. You log in and click Allow
    3. Saves token.json to google_credentials/
    4. Done — the app uses token.json silently from here

Token auto-refreshes, so you never need to run this again
unless you revoke access in your Google account settings.
"""
import sys
import os
from pathlib import Path

# Add backend/ to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ── Scopes needed ─────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/calendar",          # read + write calendar
    "https://www.googleapis.com/auth/gmail.send",        # send emails
    "https://www.googleapis.com/auth/gmail.readonly",    # read emails/labels
    "https://www.googleapis.com/auth/gmail.compose",     # compose/draft emails
]

credentials_path = Path(settings.google_credentials_path)
token_path = Path(settings.google_token_path)


def run_auth():
    if not credentials_path.exists():
        print(f"❌ credentials.json not found at {credentials_path}")
        print()
        print("Follow these steps:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project → Enable Calendar API + Gmail API")
        print("  3. Create OAuth 2.0 credentials (Desktop app type)")
        print("  4. Download the JSON → rename to credentials.json")
        print(f"  5. Move it to: {credentials_path.absolute()}")
        sys.exit(1)

    creds = None

    # Check if token already exists and is valid
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        print("✅ token.json already exists and is valid!")
        print("   No action needed — the app can use Google APIs.")
        return

    if creds and creds.expired and creds.refresh_token:
        print("🔄 Token expired — refreshing...")
        creds.refresh(Request())
    else:
        print("🌐 Opening browser for Google login...")
        print("   Log in with your Google account and click Allow.")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)

    # Save the token
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print(f"\n✅ token.json saved to {token_path.absolute()}")
    print("   Google Calendar and Gmail are ready to use!")
    print("   You never need to run this again.")


if __name__ == "__main__":
    run_auth()