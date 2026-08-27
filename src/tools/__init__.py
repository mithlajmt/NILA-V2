"""
NILA-V2 Agentic Tool System
Provides modular tool registration, schema conversion for Gemini Live & OpenAI, and async execution dispatch.
"""

from .registry import ToolRegistry, register_tool
from .built_in_tools import get_current_time, get_weather, trigger_robot_gesture, trigger_n8n_workflow
from .gmail_tools import read_unread_emails, create_gmail_draft, send_gmail_draft, send_gmail_message, get_email_details
from .calendar_tools import get_today_schedule, get_calendar_events, create_calendar_event
from .telegram_user import send_telegram_user_message, read_telegram_user_messages, get_recent_telegram_chats
from .telegram_bot import send_telegram_bot_message, read_telegram_bot_messages

__all__ = [
    "ToolRegistry",
    "register_tool",
    "get_current_time",
    "get_weather",
    "trigger_robot_gesture",
    "trigger_n8n_workflow",
    "read_unread_emails",
    "create_gmail_draft",
    "send_gmail_draft",
    "send_gmail_message",
    "get_email_details",
    "get_today_schedule",
    "get_calendar_events",
    "create_calendar_event",
    "send_telegram_user_message",
    "read_telegram_user_messages",
    "get_recent_telegram_chats",
    "send_telegram_bot_message",
    "read_telegram_bot_messages",
]



