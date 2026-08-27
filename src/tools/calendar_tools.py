"""
NILA-V2 Native Google Calendar Agentic Tools
---------------------------------------------
Modular tools enabling Nila to read daily schedules, check upcoming events,
and create new calendar meetings via Google Calendar API.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, List

from src.tools.registry import register_tool

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/calendar'
]

# Paths for Credentials
CREDENTIALS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "credentials"
TOKEN_PATH = CREDENTIALS_DIR / "gmail_token.json"
CLIENT_SECRET_PATH = CREDENTIALS_DIR / "client_secret.json"


def get_calendar_service():
    """
    Authenticate and return a Google Calendar API service client.
    Handles token load, refresh, and OAuth flow.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as e:
        logger.error(f"❌ Google API Python libraries not installed: {e}")
        return None

    creds = None
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)

    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
            if creds and hasattr(creds, 'scopes') and creds.scopes:
                missing_scopes = [s for s in SCOPES if s not in creds.scopes]
                if missing_scopes:
                    logger.warning(f"⚠️ Token missing required scopes {missing_scopes}. Refreshing OAuth authorization...")
                    creds = None
        except Exception as te:
            logger.warning(f"⚠️ Error loading saved token from {TOKEN_PATH}: {te}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as re:
                logger.warning(f"⚠️ Refreshing token failed: {re}. Re-authenticating...")
                creds = None

        if not creds:
            if not CLIENT_SECRET_PATH.exists():
                logger.error(
                    f"❌ OAuth credentials file not found at '{CLIENT_SECRET_PATH}'!\n"
                    f"Please save client secret from Google Cloud Console to {CLIENT_SECRET_PATH}."
                )
                return None

            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        logger.info(f"✅ Saved OAuth token to {TOKEN_PATH}")

    return build('calendar', 'v3', credentials=creds)



# ---------------------------------------------------------------------------
# Tool 1: Get Today's Schedule
# ---------------------------------------------------------------------------
@register_tool(
    name="get_today_schedule",
    description="Get today's agenda, meetings, and events from Google Calendar.",
    parameters={
        "type": "OBJECT",
        "properties": {},
        "required": [],
    },
)
def get_today_schedule() -> str:
    """Fetch all events scheduled for today from primary Google Calendar."""
    service = get_calendar_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Google Calendar service not initialized. Missing credentials."
        })

    try:
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()
        end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return json.dumps({
                "status": "success",
                "count": 0,
                "summary": "You have no events scheduled for today.",
                "events": []
            }, ensure_ascii=False)

        event_list = []
        for ev in events:
            start = ev['start'].get('dateTime', ev['start'].get('date'))
            end = ev['end'].get('dateTime', ev['end'].get('date'))
            summary = ev.get('summary', '(No Title)')
            location = ev.get('location', '')
            description = ev.get('description', '')

            event_list.append({
                "id": ev['id'],
                "title": summary,
                "start": start,
                "end": end,
                "location": location,
                "description": description
            })

        summary = f"You have {len(event_list)} event(s) scheduled for today."
        return json.dumps({
            "status": "success",
            "count": len(event_list),
            "summary": summary,
            "events": event_list
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error fetching today's schedule: {e}")
        return json.dumps({"status": "error", "message": f"Failed to fetch today's schedule: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 2: Get Upcoming Calendar Events (N Days Ahead)
# ---------------------------------------------------------------------------
@register_tool(
    name="get_calendar_events",
    description="Fetch upcoming meetings and events from Google Calendar for the next N days.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "days_ahead": {
                "type": "INTEGER",
                "description": "Number of days ahead to search (default: 7 days)",
            },
            "max_results": {
                "type": "INTEGER",
                "description": "Maximum number of events to return (default: 10)",
            }
        },
        "required": [],
    },
)
def get_calendar_events(days_ahead: int = 7, max_results: int = 10) -> str:
    """Fetch upcoming Google Calendar events."""
    service = get_calendar_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Google Calendar service not initialized. Missing credentials."
        })

    try:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days_ahead)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=future.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return json.dumps({
                "status": "success",
                "count": 0,
                "summary": f"No upcoming events found for the next {days_ahead} days.",
                "events": []
            }, ensure_ascii=False)

        event_list = []
        for ev in events:
            start = ev['start'].get('dateTime', ev['start'].get('date'))
            end = ev['end'].get('dateTime', ev['end'].get('date'))
            summary = ev.get('summary', '(No Title)')
            location = ev.get('location', '')

            event_list.append({
                "id": ev['id'],
                "title": summary,
                "start": start,
                "end": end,
                "location": location
            })

        summary = f"Found {len(event_list)} upcoming event(s) for the next {days_ahead} days."
        return json.dumps({
            "status": "success",
            "count": len(event_list),
            "summary": summary,
            "events": event_list
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error fetching calendar events: {e}")
        return json.dumps({"status": "error", "message": f"Failed to fetch calendar events: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 3: Create Calendar Event
# ---------------------------------------------------------------------------
@register_tool(
    name="create_calendar_event",
    description="Create a new event or meeting on Google Calendar.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "summary": {
                "type": "STRING",
                "description": "Title/summary of the meeting or event (e.g. 'Project Sync')",
            },
            "start_time_iso": {
                "type": "STRING",
                "description": "Start time in ISO format or relative description (e.g. '2026-08-28T10:00:00')",
            },
            "duration_minutes": {
                "type": "INTEGER",
                "description": "Duration of event in minutes (default: 30)",
            },
            "description": {
                "type": "STRING",
                "description": "Optional notes or details for the event",
            }
        },
        "required": ["summary", "start_time_iso"],
    },
)
def create_calendar_event(
    summary: str,
    start_time_iso: str,
    duration_minutes: int = 30,
    description: str = ""
) -> str:
    """Create a new event on Google Calendar."""
    service = get_calendar_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Google Calendar service not initialized. Missing credentials."
        })

    try:
        # Parse ISO string or default to current time
        try:
            start_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
        except Exception:
            start_dt = datetime.now(timezone.utc) + timedelta(hours=1)

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_body = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
            },
            'end': {
                'dateTime': end_dt.isoformat(),
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        event_id = created_event.get('id', '')
        html_link = created_event.get('htmlLink', '')

        msg = f"Successfully created event '{summary}' starting at {start_dt.strftime('%Y-%m-%d %I:%M %p')}."
        logger.info(f"📅 [CALENDAR CREATED] {msg} (ID: {event_id})")

        return json.dumps({
            "status": "success",
            "event_id": event_id,
            "title": summary,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "html_link": html_link,
            "summary": msg
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error creating calendar event: {e}")
        return json.dumps({"status": "error", "message": f"Failed to create calendar event: {str(e)}"})
