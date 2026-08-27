"""
NILA-V2 Personal Telegram User Account Tool (Telethon MTProto)
Allows Nila to send messages directly from your personal Telegram account and read incoming messages.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional
from telethon import TelegramClient
from telethon.errors import RPCError
from src.tools.registry import register_tool

logger = logging.getLogger(__name__)

# Global Telethon Client Instance
_telethon_client: Optional[TelegramClient] = None
_client_lock = asyncio.Lock()


async def get_telegram_client() -> Optional[TelegramClient]:
    """Get or initialize active Telethon TelegramClient instance"""
    global _telethon_client
    from dotenv import load_dotenv
    load_dotenv()

    api_id_val = os.getenv("TELEGRAM_API_ID", "0")
    try:
        api_id = int(api_id_val) if api_id_val else 0
    except ValueError:
        api_id = 0

    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    session_name = os.getenv("TELEGRAM_SESSION_PATH", "data/telegram_user")

    if not api_id or not api_hash:
        logger.warning("⚠️ TELEGRAM_API_ID or TELEGRAM_API_HASH missing in .env")
        return None

    # Ensure data directory exists
    os.makedirs(os.path.dirname(session_name) or "data", exist_ok=True)

    async with _client_lock:
        if _telethon_client is None:
            _telethon_client = TelegramClient(session_name, api_id, api_hash)

        if not _telethon_client.is_connected():
            await _telethon_client.connect()

        if not await _telethon_client.is_user_authorized():
            logger.warning("⚠️ Telegram User Client is not authorized. Please run 'python3 scripts/setup_telegram_user.py' first.")
            return None

    return _telethon_client


# ---------------------------------------------------------------------------
# Tool: Send Personal Telegram Message
# ---------------------------------------------------------------------------
@register_tool(
    name="send_telegram_user_message",
    description="Send a message directly from your personal Telegram account to a contact, username, or group (e.g. 'shahul', '@shahul', 'Rahul').",
    parameters={
        "type": "OBJECT",
        "properties": {
            "recipient": {
                "type": "STRING",
                "description": "Recipient name, username, phone number, or chat title (e.g. 'shahul', '@shahul_dev')",
            },
            "message": {
                "type": "STRING",
                "description": "The exact text message content to send",
            }
        },
        "required": ["recipient", "message"],
    },
)
async def send_telegram_user_message(recipient: str, message: str) -> str:
    """Send personal Telegram message via Telethon MTProto"""
    client = await get_telegram_client()

    if client is None:
        from src.tools.telegram_bot import send_telegram_bot_message
        logger.info("ℹ️ Fallback: Telegram User Client not configured; delegating to Telegram Bot API tool.")
        return send_telegram_bot_message(message=message)

    try:
        # Search dialogs for contact if not a username / phone
        target_entity = recipient
        if not recipient.startswith("@") and not recipient.startswith("+") and not recipient.isdigit():
            recip_clean = recipient.lower().strip()
            recip_words = recip_clean.split()
            best_match = None
            best_score = 0

            async for dialog in client.iter_dialogs(limit=100):
                name = dialog.name.lower().strip()
                if not name:
                    continue

                # Check 1: Exact or substring match
                if recip_clean == name or recip_clean in name or name in recip_clean:
                    best_match = dialog
                    break

                # Check 2: Word-by-word token overlap
                name_words = name.split()
                score = sum(1 for rw in recip_words if any(rw in nw for nw in name_words))
                if score > best_score:
                    best_score = score
                    best_match = dialog

            if best_match:
                target_entity = best_match.entity
                logger.info(f"Matched contact '{recipient}' -> '{best_match.name}'")

        sent_msg = await client.send_message(target_entity, message)
        result_msg = f"Successfully sent Telegram message to '{recipient}': \"{message}\""
        logger.info(f"✅ {result_msg}")
        return json.dumps({
            "status": "success",
            "recipient": recipient,
            "message_id": sent_msg.id,
            "summary": result_msg
        }, ensure_ascii=False)

    except Exception as e:
        error_str = f"Failed to send Telegram message to '{recipient}': {str(e)}"
        logger.error(f"❌ {error_str}")
        return json.dumps({
            "status": "error",
            "recipient": recipient,
            "message": error_str
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: Read Personal Telegram Messages
# ---------------------------------------------------------------------------
@register_tool(
    name="read_telegram_user_messages",
    description="Read recent incoming messages from your personal Telegram account chats.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "chat": {
                "type": "STRING",
                "description": "Optional contact name or username to filter messages from. Leave empty to read latest messages from all recent chats.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Number of recent messages to retrieve (default: 5)",
            }
        },
        "required": [],
    },
)
async def read_telegram_user_messages(chat: str = "", limit: int = 5) -> str:
    """Read recent personal Telegram messages via Telethon"""
    client = await get_telegram_client()

    if client is None:
        from src.tools.telegram_bot import read_telegram_bot_messages
        logger.info("ℹ️ Fallback: Telegram User Client not configured; delegating to Telegram Bot API tool.")
        return read_telegram_bot_messages(limit=limit)

    try:
        messages_data = []

        if chat:
            # Read from specific chat
            target = chat
            if not chat.startswith("@") and not chat.startswith("+") and not chat.isdigit():
                async for dialog in client.iter_dialogs(limit=50):
                    if chat.lower() in dialog.name.lower():
                        target = dialog.entity
                        break

            async for msg in client.iter_messages(target, limit=limit):
                if msg.text:
                    sender = await msg.get_sender()
                    sender_name = getattr(sender, "first_name", "Unknown") if sender else "Unknown"
                    messages_data.append({
                        "sender": sender_name,
                        "text": msg.text,
                        "date": msg.date.strftime("%H:%M, %b %d")
                    })
        else:
            # Read latest from all recent dialogs
            async for dialog in client.iter_dialogs(limit=limit):
                if dialog.message and dialog.message.text:
                    messages_data.append({
                        "chat": dialog.name,
                        "text": dialog.message.text,
                        "date": dialog.message.date.strftime("%H:%M, %b %d")
                    })

        summary = f"Retrieved {len(messages_data)} recent Telegram messages."
        logger.info(f"✅ {summary}")
        return json.dumps({
            "status": "success",
            "count": len(messages_data),
            "messages": messages_data,
            "summary": summary
        }, ensure_ascii=False)

    except Exception as e:
        error_str = f"Failed to read Telegram messages: {str(e)}"
        logger.error(f"❌ {error_str}")
        return json.dumps({
            "status": "error",
            "message": error_str
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: Get Active Telegram Contacts & Recent Chat List
# ---------------------------------------------------------------------------
@register_tool(
    name="get_recent_telegram_chats",
    description="List active contacts and recent Telegram chat names from your personal Telegram account.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "limit": {
                "type": "INTEGER",
                "description": "Number of recent active chats to return (default: 20)",
            }
        },
        "required": [],
    },
)
async def get_recent_telegram_chats(limit: int = 20) -> str:
    """Get list of active contacts and chat names"""
    client = await get_telegram_client()

    if client is None:
        return json.dumps({"status": "error", "message": "Telegram user account not logged in."}, ensure_ascii=False)

    try:
        chats = []
        async for dialog in client.iter_dialogs(limit=limit):
            chats.append({
                "name": dialog.name,
                "is_user": dialog.is_user,
                "is_group": dialog.is_group,
                "unread": dialog.unread_count
            })

        return json.dumps({
            "status": "success",
            "total": len(chats),
            "chats": chats,
            "summary": f"Retrieved {len(chats)} active Telegram contacts/chats: " + ", ".join(c["name"] for c in chats[:10])
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
