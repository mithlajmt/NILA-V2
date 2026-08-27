"""
NILA-V2 Telegram Bot API Tool (Zero Web Portal Setup Required)
Uses official Telegram Bot Token (from @BotFather in 30 seconds).
Delivers instant notifications to your personal Telegram app.
"""

import asyncio
import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from src.tools.registry import register_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool: Send Telegram Bot Message
# ---------------------------------------------------------------------------
@register_tool(
    name="send_telegram_bot_message",
    description="Send an instant message directly to your personal Telegram app via Telegram Bot API.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "message": {
                "type": "STRING",
                "description": "The exact text message to send to Telegram",
            },
            "chat_id": {
                "type": "STRING",
                "description": "Optional Telegram Chat ID. Leave empty to use your default personal chat ID from .env",
            }
        },
        "required": ["message"],
    },
)
def send_telegram_bot_message(message: str, chat_id: str = "") -> str:
    """Send message via Telegram Bot HTTP API"""
    from dotenv import load_dotenv
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    target_chat = chat_id or os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token:
        err = "TELEGRAM_BOT_TOKEN missing in .env. Please get a token from @BotFather on Telegram in 30 seconds."
        logger.warning(f"⚠️ {err}")
        return json.dumps({"status": "error", "message": err}, ensure_ascii=False)

    if not target_chat:
        err = "TELEGRAM_CHAT_ID missing in .env. Send any message to your bot on Telegram first."
        logger.warning(f"⚠️ {err}")
        return json.dumps({"status": "error", "message": err}, ensure_ascii=False)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": target_chat,
        "text": message,
        "parse_mode": "HTML"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "NILA-V2-Robot"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data.get("ok"):
                msg = f"Successfully delivered message to Telegram: \"{message}\""
                logger.info(f"✅ [TELEGRAM BOT] {msg}")
                return json.dumps({"status": "success", "summary": msg}, ensure_ascii=False)
            else:
                err_msg = data.get("description", "Unknown Telegram API error")
                logger.error(f"❌ Telegram API Error: {err_msg}")
                return json.dumps({"status": "error", "message": err_msg}, ensure_ascii=False)
    except Exception as e:
        err = f"Failed to send Telegram message: {str(e)}"
        logger.error(f"❌ {err}")
        return json.dumps({"status": "error", "message": err}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: Read Incoming Telegram Bot Messages
# ---------------------------------------------------------------------------
@register_tool(
    name="read_telegram_bot_messages",
    description="Read recent incoming messages sent by you to your Telegram Bot.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "limit": {
                "type": "INTEGER",
                "description": "Number of recent messages to retrieve (default: 5)",
            }
        },
        "required": [],
    },
)
def read_telegram_bot_messages(limit: int = 5) -> str:
    """Get latest updates sent to Telegram Bot"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    if not bot_token:
        return json.dumps({
            "status": "error",
            "message": "TELEGRAM_BOT_TOKEN missing in .env."
        }, ensure_ascii=False)

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates?limit=10"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NILA-V2-Robot"})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
            if not data.get("ok"):
                return json.dumps({"status": "error", "message": "Failed to fetch Telegram updates"}, ensure_ascii=False)

            results = data.get("result", [])
            messages = []

            for update in results[-limit:]:
                if "message" in update and "text" in update["message"]:
                    msg_obj = update["message"]
                    sender = msg_obj.get("from", {}).get("first_name", "User")
                    text = msg_obj.get("text", "")
                    chat_id = msg_obj.get("chat", {}).get("id", "")
                    messages.append({
                        "sender": sender,
                        "chat_id": chat_id,
                        "text": text
                    })

            summary = f"Retrieved {len(messages)} recent messages from Telegram Bot."
            logger.info(f"✅ {summary}")
            return json.dumps({
                "status": "success",
                "count": len(messages),
                "messages": messages,
                "summary": summary
            }, ensure_ascii=False)

    except Exception as e:
        err = f"Error reading Telegram Bot messages: {str(e)}"
        logger.error(f"❌ {err}")
        return json.dumps({"status": "error", "message": err}, ensure_ascii=False)
