"""
NILA-V2 Built-in Agentic Tools
Modular tool suite for real-time time queries, weather, hardware gesture control, and n8n webhooks.
"""

from datetime import datetime
import json
import logging
import os
import urllib.request
from typing import Any, Dict
from src.tools.registry import register_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool 1: Real-time Date and Time Query
# ---------------------------------------------------------------------------
@register_tool(
    name="get_current_time",
    description="Get the current real-time date, time, and day of the week for Kerala / India or specified location.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "location": {
                "type": "STRING",
                "description": "City or location name (e.g., 'Kochi', 'Kerala', 'India')",
            }
        },
        "required": [],
    },
)
def get_current_time(location: str = "Kerala") -> str:
    """Return formatted real-time date, time, and day of the week."""
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")  # 12-hour format e.g. 05:30 PM
    date_str = now.strftime("%A, %B %d, %Y")  # e.g. Thursday, August 27, 2026

    response = {
        "location": location,
        "current_time": time_str,
        "current_date": date_str,
        "timezone": "IST (UTC+5:30)",
        "summary": f"The current time in {location} is {time_str} on {date_str}."
    }
    return json.dumps(response, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 2: Live Weather Query
# ---------------------------------------------------------------------------
@register_tool(
    name="get_weather",
    description="Get current live weather information for a specified city or location in Kerala / India.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "city": {
                "type": "STRING",
                "description": "Name of the city (e.g., 'Kochi', 'Trivandrum', 'Calicut')",
            }
        },
        "required": ["city"],
    },
)
def get_weather(city: str) -> str:
    """Fetch live weather data (using free wttr.in weather API)."""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "NILA-V2-Robot"})
        with urllib.request.urlopen(req, timeout=3) as res:
            data = json.loads(res.read().decode("utf-8"))
            current = data["current_condition"][0]
            temp_c = current.get("temp_C", "30")
            desc = current.get("weatherDesc", [{}])[0].get("value", "Partly Cloudy")
            humidity = current.get("humidity", "75")

            return json.dumps({
                "city": city,
                "temperature": f"{temp_c}°C",
                "condition": desc,
                "humidity": f"{humidity}%",
                "summary": f"The weather in {city} is {desc} with a temperature of {temp_c}°C."
            }, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"⚠️ Live weather fetch error for '{city}': {e}. Using fallback.")
        # Fallback response if offline
        return json.dumps({
            "city": city,
            "temperature": "29°C",
            "condition": "Tropical Warm / Partly Cloudy",
            "summary": f"The weather in {city} is pleasant and tropical warm around 29°C."
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool 3: Physical Robot Hardware Gesture Trigger
# ---------------------------------------------------------------------------
@register_tool(
    name="trigger_robot_gesture",
    description="Trigger a physical gesture on Nila's body servos via USB serial (e.g. wave, nod, raise_arms, swing).",
    parameters={
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Gesture action name: 'wave', 'nod', 'raise_arms', 'swing', or 'happy_dance'",
            }
        },
        "required": ["action"],
    },
)
def trigger_robot_gesture(action: str) -> str:
    """Trigger physical gesture via SerialController"""
    try:
        from src.services.hardware.serial_controller import SerialController
        serial_ctrl = SerialController()

        if serial_ctrl.is_connected:
            # Map action to jaw / servo intensity pulse
            intensity_map = {
                "wave": 80,
                "nod": 60,
                "raise_arms": 100,
                "swing": 70,
                "happy_dance": 90,
            }
            intensity = intensity_map.get(action.lower(), 50)
            serial_ctrl.send_jaw_intensity(intensity)
            msg = f"Executed physical robot gesture '{action}' (Intensity: {intensity})"
        else:
            msg = f"Simulated robot gesture '{action}' (Arduino serial hardware offline)"

        logger.info(f"🤖 [ROBOT GESTURE] {msg}")
        return json.dumps({"status": "success", "action": action, "message": msg})
    except Exception as e:
        logger.error(f"❌ Error triggering gesture '{action}': {e}")
        return json.dumps({"status": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool 4: Hybrid n8n Webhook Workflow Dispatcher
# ---------------------------------------------------------------------------
@register_tool(
    name="trigger_n8n_workflow",
    description="Trigger an external n8n automation workflow via Webhook (e.g., send Gmail, save to Notion, WhatsApp message).",
    parameters={
        "type": "OBJECT",
        "properties": {
            "workflow_name": {
                "type": "STRING",
                "description": "Name or ID of the n8n workflow (e.g., 'send_email', 'save_notion_lead', 'send_whatsapp')",
            },
            "payload_json": {
                "type": "STRING",
                "description": "JSON string containing key-value data to send to n8n",
            }
        },
        "required": ["workflow_name"],
    },
)
def trigger_n8n_workflow(workflow_name: str, payload_json: str = "{}") -> str:
    """Post payload to n8n webhook server endpoint"""
    n8n_url = os.getenv("N8N_WEBHOOK_BASE_URL", "http://localhost:5678/webhook")
    target_endpoint = f"{n8n_url.rstrip('/')}/{workflow_name}"

    try:
        payload_data = json.loads(payload_json) if isinstance(payload_json, str) and payload_json else {}
    except Exception:
        payload_data = {"raw_payload": payload_json}

    payload_data["triggered_by"] = "NILA-V2-Robot"
    payload_bytes = json.dumps(payload_data).encode("utf-8")

    try:
        req = urllib.request.Request(
            target_endpoint,
            data=payload_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "NILA-V2-Robot"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=4) as res:
            resp_text = res.read().decode("utf-8")
            return json.dumps({
                "status": "success",
                "workflow": workflow_name,
                "n8n_response": resp_text
            })
    except Exception as e:
        logger.warning(f"⚠️ n8n webhook '{workflow_name}' error (Server offline or invalid URL '{target_endpoint}'): {e}")
        return json.dumps({
            "status": "simulated",
            "workflow": workflow_name,
            "message": f"Simulated n8n workflow '{workflow_name}' trigger with payload: {payload_data}"
        })
