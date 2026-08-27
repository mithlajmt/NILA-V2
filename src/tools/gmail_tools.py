"""
NILA-V2 Native Gmail Agentic Tools
----------------------------------
Modular tools enabling Nila to read unread emails, search inbox, inspect email details,
create email drafts, and send outgoing emails via Google Gmail API.
"""

import base64
from email.mime.text import MIMEText
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


def get_gmail_service():
    """
    Authenticate and return a Gmail API service client.
    Handles token load, refresh, and OAuth flow if needed.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as e:
        logger.error(f"❌ Gmail API Python libraries not installed: {e}")
        return None

    creds = None
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)

    # 1. Load saved token if present
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


    # 2. Refresh or trigger OAuth login if missing/invalid
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
                    f"❌ Gmail OAuth credentials file not found at '{CLIENT_SECRET_PATH}'!\n"
                    f"Please download OAuth client secret from Google Cloud Console and save to {CLIENT_SECRET_PATH}."
                )
                return None

            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for future runs
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        logger.info(f"✅ Saved Gmail OAuth token to {TOKEN_PATH}")

    return build('gmail', 'v1', credentials=creds)


# ---------------------------------------------------------------------------
# Tool 1: Read & Search Unread Emails
# ---------------------------------------------------------------------------
@register_tool(
    name="read_unread_emails",
    description="Fetch and list recent unread emails or search emails in Gmail inbox (e.g. from a specific sender or topic).",
    parameters={
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "Optional search filter (e.g. 'is:unread', 'from:Rahul', 'label:INBOX'). Default is 'is:unread'.",
            },
            "max_results": {
                "type": "INTEGER",
                "description": "Maximum number of email messages to retrieve (default: 5).",
            }
        },
        "required": [],
    },
)
def read_unread_emails(query: str = "is:unread", max_results: int = 5) -> str:
    """Fetch recent unread emails matching query from Gmail API."""
    service = get_gmail_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Gmail API service not initialized. Missing '{CLIENT_SECRET_PATH}' or '{TOKEN_PATH}'."
        })

    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            return json.dumps({
                "status": "success",
                "count": 0,
                "query": query,
                "summary": f"No emails found matching query '{query}'.",
                "emails": []
            }, ensure_ascii=False)

        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            snippet = msg_data.get('snippet', '')

            email_list.append({
                "id": msg['id'],
                "from": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet
            })

        summary = f"Found {len(email_list)} email(s) for query '{query}'."
        return json.dumps({
            "status": "success",
            "count": len(email_list),
            "query": query,
            "summary": summary,
            "emails": email_list
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error reading emails: {e}")
        return json.dumps({"status": "error", "message": f"Error fetching emails: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 2: Create Email Draft (Safe Confirmation Step 1)
# ---------------------------------------------------------------------------
@register_tool(
    name="create_gmail_draft",
    description="Create a draft email in Gmail without sending it immediately. ALWAYS use this tool FIRST when a user requests to compose or send an email. After calling this, ask the user for explicit confirmation before calling send_gmail_draft.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "to_email": {
                "type": "STRING",
                "description": "Recipient's email address (e.g. 'user@example.com')",
            },
            "subject": {
                "type": "STRING",
                "description": "Subject line of the email",
            },
            "body": {
                "type": "STRING",
                "description": "Plain text body content of the email",
            }
        },
        "required": ["to_email", "subject", "body"],
    },
)
def create_gmail_draft(to_email: str, subject: str, body: str) -> str:
    """Create a draft email message in Gmail."""
    service = get_gmail_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Gmail API service not initialized. Missing '{CLIENT_SECRET_PATH}' or '{TOKEN_PATH}'."
        })

    try:
        mime_message = MIMEText(body)
        mime_message['to'] = to_email
        mime_message['subject'] = subject
        raw_string = base64.urlsafe_b64encode(mime_message.as_bytes()).decode('utf-8')

        draft_body = {'message': {'raw': raw_string}}
        draft_res = service.users().drafts().create(userId='me', body=draft_body).execute()
        draft_id = draft_res.get('id', '')

        summary = f"Created email draft to '{to_email}' with subject '{subject}'. Ask user for confirmation before sending draft ID '{draft_id}'."
        logger.info(f"📝 [GMAIL DRAFT CREATED] {summary}")

        return json.dumps({
            "status": "success",
            "draft_id": draft_id,
            "to": to_email,
            "subject": subject,
            "body": body,
            "summary": f"Draft created for {to_email} with subject '{subject}'. Ask user: 'I have drafted the email to {to_email}. Would you like me to send it now?'"
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error creating Gmail draft: {e}")
        return json.dumps({"status": "error", "message": f"Failed to create email draft: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 3: Send Confirmed Draft (Safe Confirmation Step 2)
# ---------------------------------------------------------------------------
@register_tool(
    name="send_gmail_draft",
    description="Send an existing Gmail draft by its draft ID. ONLY call this tool AFTER the user gives explicit voice confirmation (e.g. 'Yes, send it').",
    parameters={
        "type": "OBJECT",
        "properties": {
            "draft_id": {
                "type": "STRING",
                "description": "The unique draft ID returned by create_gmail_draft",
            }
        },
        "required": ["draft_id"],
    },
)
def send_gmail_draft(draft_id: str) -> str:
    """Send a Gmail draft by draft_id."""
    service = get_gmail_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Gmail API service not initialized. Missing '{CLIENT_SECRET_PATH}' or '{TOKEN_PATH}'."
        })

    try:
        sent_msg = service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
        msg_id = sent_msg.get('id', '')

        summary = f"Successfully sent draft email (Draft ID: {draft_id}, Sent Message ID: {msg_id})."
        logger.info(f"📧 [GMAIL DRAFT SENT] {summary}")

        return json.dumps({
            "status": "success",
            "draft_id": draft_id,
            "message_id": msg_id,
            "summary": summary
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error sending Gmail draft '{draft_id}': {e}")
        return json.dumps({"status": "error", "message": f"Failed to send draft: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 4: Direct Send Gmail Message (Emergency / Explicit Direct Trigger)
# ---------------------------------------------------------------------------
@register_tool(
    name="send_gmail_message",
    description="Directly send an outgoing email message via Gmail. WARNING: Prefer calling create_gmail_draft first unless the user has ALREADY explicitly confirmed sending.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "to_email": {
                "type": "STRING",
                "description": "Recipient's email address (e.g. 'user@example.com')",
            },
            "subject": {
                "type": "STRING",
                "description": "Subject line of the email",
            },
            "body": {
                "type": "STRING",
                "description": "Plain text body content of the email",
            }
        },
        "required": ["to_email", "subject", "body"],
    },
)
def send_gmail_message(to_email: str, subject: str, body: str) -> str:
    """Send an email directly using Gmail API."""
    service = get_gmail_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Gmail API service not initialized. Missing '{CLIENT_SECRET_PATH}' or '{TOKEN_PATH}'."
        })

    try:
        mime_message = MIMEText(body)
        mime_message['to'] = to_email
        mime_message['subject'] = subject
        raw_string = base64.urlsafe_b64encode(mime_message.as_bytes()).decode('utf-8')

        sent_msg = service.users().messages().send(userId='me', body={'raw': raw_string}).execute()
        msg_id = sent_msg.get('id', '')

        summary = f"Successfully sent email to '{to_email}' with subject '{subject}'."
        logger.info(f"📧 [GMAIL SENT] {summary} (ID: {msg_id})")

        return json.dumps({
            "status": "success",
            "message_id": msg_id,
            "to": to_email,
            "subject": subject,
            "summary": summary
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error sending Gmail message: {e}")
        return json.dumps({"status": "error", "message": f"Failed to send email: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 5: Get Full Email Details by ID
# ---------------------------------------------------------------------------
@register_tool(
    name="get_email_details",
    description="Get detailed full text content of a specific email message by its email message ID.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "message_id": {
                "type": "STRING",
                "description": "The unique message ID returned by read_unread_emails",
            }
        },
        "required": ["message_id"],
    },
)
def get_email_details(message_id: str) -> str:
    """Fetch full content of an email by message_id."""
    service = get_gmail_service()
    if not service:
        return json.dumps({
            "status": "error",
            "message": f"Gmail API service not initialized. Missing '{CLIENT_SECRET_PATH}' or '{TOKEN_PATH}'."
        })

    try:
        msg_data = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        payload = msg_data.get('payload', {})
        headers = payload.get('headers', [])

        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        snippet = msg_data.get('snippet', '')

        # Extract plain text body if available
        body_text = snippet
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break

        return json.dumps({
            "status": "success",
            "id": message_id,
            "from": sender,
            "subject": subject,
            "date": date,
            "body": body_text,
            "snippet": snippet
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Error getting email details for {message_id}: {e}")
        return json.dumps({"status": "error", "message": f"Failed to retrieve email details: {str(e)}"})
