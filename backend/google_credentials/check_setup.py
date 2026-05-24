"""Quick auth and API check for Gmail + Calendar.

Run this from the repo root with the backend venv activated:

PYTHONPATH=./backend ./backend/venv/bin/python ./backend/google_credentials/check_setup.py

It will print the email address from the token, list next 5 calendar events, and try to send a test email (to the same account) if you confirm.
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


def load_credentials(scopes):
    token_path = Path(settings.google_token_path)
    if not token_path.exists():
        print(f"token.json not found at {token_path}. Run: python google_credentials/auth_setup.py")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    return creds


def gmail_profile(creds):
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    return profile


def list_calendar_events(creds, days_ahead=7):
    service = build('calendar', 'v3', credentials=creds)
    from datetime import datetime, timedelta
    now = datetime.utcnow().isoformat() + 'Z'
    end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
    events = (
        service.events()
        .list(calendarId='primary', timeMin=now, timeMax=end, maxResults=10, singleEvents=True, orderBy='startTime')
        .execute()
    )
    return events.get('items', [])


def try_send_test_email(creds, to_address):
    service = build('gmail', 'v1', credentials=creds)
    from email.mime.text import MIMEText
    import base64

    body = 'Test email from HR Agent. If you receive this, Gmail API send works.'
    message = MIMEText(body)
    message['to'] = to_address
    message['subject'] = 'HR Agent — test email'
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return sent


def main():
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/calendar',
    ]
    creds = load_credentials(SCOPES)

    print('Credentials loaded from:', settings.google_token_path)
    profile = gmail_profile(creds)
    print('Gmail profile:')
    print('  Email:', profile.get('emailAddress'))

    events = list_calendar_events(creds, days_ahead=7)
    print(f'Next {len(events)} calendar events (next 7 days):')
    for e in events[:5]:
        start = e.get('start', {}).get('dateTime', e.get('start', {}).get('date'))
        print(' -', e.get('summary', '(no title)'), '@', start)

    ans = input('Attempt to send a test email to your account? (y/N): ').strip().lower()
    if ans == 'y':
        to_addr = profile.get('emailAddress')
        print('Sending test email to', to_addr)
        sent = try_send_test_email(creds, to_addr)
        print('Sent message id:', sent.get('id'))
    else:
        print('Skipped sending test email.')


if __name__ == '__main__':
    main()
