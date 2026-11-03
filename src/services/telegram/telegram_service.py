"""
NILA-V2 Telegram Remote Control & Telemetry Service
----------------------------------------------------
Provides complete remote control, status monitoring, camera snapshots,
and crash recovery for NILA from anywhere via Telegram.

Features:
- Instant interactive keyboard (Hand Up/Down, Camera Snapshot, Status, Logs, Restart)
- Live Camera Snapshots directly from shared memory (Zero CPU lag)
- System Vitals & Diagnostics (Mic, Speaker, Camera, IP, CPU Temp, RAM)
- Say aloud: /say <text> converts text to speech on Nila
- Wi-Fi manager: /wifi and /addwifi <ssid> <password>
- Safe remote restart: /restart reboots nila.service
- Strict access security: only responds to configured TELEGRAM_CHAT_ID
"""

import asyncio
import collections
import concurrent.futures
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TelegramService:
    """Manages Telegram Bot integration, background polling, and remote control"""

    def __init__(self, settings, robot=None):
        self.settings = settings
        self.robot = robot
        self.logger = logging.getLogger(__name__)

        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or getattr(settings, "TELEGRAM_CHAT_ID", "").strip()

        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="TelegramWorker")
        self.last_update_id = 0
        self.start_time = time.time()
        self._is_restarting = False

        # Keyboard layout
        self.keyboard_markup = {
            "keyboard": [
                [{"text": "🖐️ Hand UP"}, {"text": "🖐️ Hand DOWN"}, {"text": "👋 Wave"}],
                [{"text": "📸 Camera Snap"}, {"text": "📊 System Status"}],
                [{"text": "📜 Recent Logs"}, {"text": "📶 Wi-Fi Status"}],
                [{"text": "🔄 Restart Nila"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }

        # Subscribe to EventBus for critical alerts
        self._subscribe_events()

    def _subscribe_events(self):
        """Subscribe to system events for alerts"""
        try:
            from src.core.event_bus import EventBus
            from src.core.events import StateChangeEvent
            self.event_bus = EventBus()
            self.event_bus.subscribe("state.change", self._handle_state_event)
        except Exception as e:
            self.logger.warning(f"⚠️ EventBus subscription in TelegramService: {e}")

    def _handle_state_event(self, event):
        """Handle state change event"""
        pass

    def start(self):
        """Start Telegram Bot long-polling daemon thread"""
        if not self.bot_token:
            self.logger.warning("⚠️ TELEGRAM_BOT_TOKEN is not set in .env. Telegram service disabled.")
            return

        if not self.chat_id:
            self.logger.warning("⚠️ TELEGRAM_CHAT_ID is not set in .env. Telegram service disabled.")
            return

        # Flush any stale unacknowledged updates from prior runs so old clicks don't replay
        try:
            stale_updates = self.get_updates(offset=-1, timeout=0)
            if stale_updates:
                self.last_update_id = max(u.get("update_id", 0) for u in stale_updates)
                # Confirm receipt with Telegram API
                self.get_updates(offset=self.last_update_id + 1, timeout=0)
        except Exception:
            pass

        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True,
            name="TelegramBotWorker"
        )
        self.worker_thread.start()
        self.logger.info("🟢 Telegram Bot Remote & Telemetry Service started.")

        # Send startup notification to authorized user
        self.executor.submit(self._send_startup_greeting)

    def _send_startup_greeting(self):
        """Send greeting and keyboard to owner on startup"""
        time.sleep(2.0)  # Wait for robot services to finish initializing
        ip = self._get_ip_address()
        greeting = (
            f"🤖 <b>NILA-V2 is Online & Ready!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <b>IP Address:</b> <code>{ip}</code>\n"
            f"📡 <b>Status:</b> Listening & Active\n"
            f"⚡ <i>Tap any button below to control Nila:</i>"
        )
        self.send_message(greeting, reply_markup=self.keyboard_markup)

    def stop(self):
        """Stop background worker thread and executor"""
        self.is_running = False
        self.logger.info("🛑 Telegram Service stopping...")
        if hasattr(self, "executor") and self.executor:
            try:
                self.executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    def cleanup(self):
        self.stop()

    # -------------------------------------------------------------------------
    # HTTP API Client Methods
    # -------------------------------------------------------------------------
    def send_message(self, text: str, reply_markup: Optional[Any] = None, parse_mode: str = "HTML") -> bool:
        """Send text message to Telegram with persistent keyboard markup"""
        if not self.bot_token or not self.chat_id:
            return False

        if reply_markup is None:
            reply_markup = self.keyboard_markup
        elif reply_markup is False:
            reply_markup = None

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "NILA-V2-Robot"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=8) as res:
                body = json.loads(res.read().decode("utf-8"))
                return bool(body.get("ok"))
        except Exception as e:
            self.logger.error(f"❌ Telegram sendMessage error: {e}")
            return False

    def send_photo(self, photo_bytes: bytes, caption: str = "", reply_markup: Optional[Any] = None) -> bool:
        """Send JPEG photo to Telegram using multipart/form-data (Standard library, 0 external deps)"""
        if not self.bot_token or not self.chat_id:
            return False

        if reply_markup is None:
            reply_markup = self.keyboard_markup
        elif reply_markup is False:
            reply_markup = None

        boundary = "----TelegramFormBoundary" + uuid.uuid4().hex[:16]
        body = bytearray()

        # chat_id
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{self.chat_id}\r\n'.encode("utf-8"))

        # caption
        if caption:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode("utf-8"))

        # reply_markup
        if reply_markup:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="reply_markup"\r\n\r\n{json.dumps(reply_markup)}\r\n'.encode("utf-8"))

        # photo file
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="photo"; filename="nila_cam.jpg"\r\n'.encode("utf-8"))
        body.extend(b"Content-Type: image/jpeg\r\n\r\n")
        body.extend(photo_bytes)
        body.extend(b"\r\n")

        # closing boundary
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        req = urllib.request.Request(
            url,
            data=bytes(body),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "NILA-V2-Robot"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as res:
                data = json.loads(res.read().decode("utf-8"))
                return bool(data.get("ok"))
        except Exception as e:
            self.logger.error(f"❌ Telegram sendPhoto error: {e}")
            return False

    def get_updates(self, offset: int = 0, timeout: int = 20) -> List[Dict]:
        """Poll for new messages with long-polling"""
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates?offset={offset}&timeout={timeout}"
        req = urllib.request.Request(url, headers={"User-Agent": "NILA-V2-Robot"})

        try:
            with urllib.request.urlopen(req, timeout=timeout + 5) as res:
                data = json.loads(res.read().decode("utf-8"))
                if data.get("ok"):
                    return data.get("result", [])
        except Exception as e:
            # Network timeout or temporary drop, normal during long-polling
            self.logger.debug(f"Telegram polling retry: {e}")
        return []

    # -------------------------------------------------------------------------
    # Polling Loop & Message Dispatcher
    # -------------------------------------------------------------------------
    def _polling_loop(self):
        """Background worker polling getUpdates"""
        self.logger.info("📡 Telegram Bot polling loop started")
        consecutive_errors = 0

        while self.is_running:
            try:
                updates = self.get_updates(offset=self.last_update_id + 1, timeout=15)
                if updates:
                    consecutive_errors = 0
                    for update in updates:
                        update_id = update.get("update_id", 0)
                        if update_id > self.last_update_id:
                            self.last_update_id = update_id

                        self._process_update(update)

                time.sleep(0.5)

            except Exception as e:
                consecutive_errors += 1
                self.logger.warning(f"⚠️ Telegram polling loop exception ({consecutive_errors}): {e}")
                time.sleep(min(10, 2 * consecutive_errors))

    def _process_update(self, update: Dict):
        """Process incoming message or callback query"""
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            return

        chat = msg.get("chat", {})
        sender_chat_id = str(chat.get("id", ""))
        text = (msg.get("text") or "").strip()

        # Strict security check: only the authorized chat ID can issue commands
        if sender_chat_id != self.chat_id:
            self.logger.warning(f"⛔ Unauthorized Telegram message from chat_id={sender_chat_id}")
            return

        if not text:
            return

        self.logger.info(f"📩 [Telegram Command] '{text}' from {chat.get('first_name', 'Owner')}")
        self._handle_command(text)

    # -------------------------------------------------------------------------
    # Command Handlers
    # -------------------------------------------------------------------------
    def _handle_command(self, text: str):
        """Dispatch commands to robot hardware and services"""
        clean_cmd = text.strip()

        # 1. Menu / Start / Help
        if clean_cmd in ("/start", "/help", "/menu", "menu", "help"):
            self._cmd_menu()

        # 2. Hand Control
        elif clean_cmd in ("🖐️ Hand UP", "/hand_up", "/handup", "hand up", "/raise"):
            self._cmd_hand(up=True)

        elif clean_cmd in ("🖐️ Hand DOWN", "/hand_down", "/handdown", "hand down", "/lower"):
            self._cmd_hand(up=False)

        # 3. Wave Hand (Send 'A')
        elif clean_cmd in ("👋 Wave", "/wave", "wave", "wave hand", "/wave_hand"):
            self._cmd_wave()

        # 4. Camera Snapshot
        elif clean_cmd in ("📸 Camera Snap", "/snap", "/photo", "/cam", "/see", "photo", "snap"):
            self._cmd_camera_snap()

        # 4. System Status & Diagnostics
        elif clean_cmd in ("📊 System Status", "/status", "status", "/info"):
            self._cmd_status()

        # 5. Recent Logs
        elif clean_cmd in ("📜 Recent Logs", "/logs", "logs", "/log"):
            self._cmd_logs()

        # 6. Wi-Fi Status
        elif clean_cmd in ("📶 Wi-Fi Status", "/wifi", "wifi"):
            self._cmd_wifi()

        # 7. Add Wi-Fi: /addwifi <SSID> <Password>
        elif clean_cmd.startswith("/addwifi ") or clean_cmd.startswith("/connect_wifi "):
            parts = clean_cmd.split(maxsplit=2)
            if len(parts) >= 3:
                ssid = parts[1]
                pwd = parts[2]
                self._cmd_add_wifi(ssid, pwd)
            else:
                self.send_message("❌ Usage: <code>/addwifi &lt;SSID&gt; &lt;PASSWORD&gt;</code>")

        # 8. Restart Nila
        elif clean_cmd in ("🔄 Restart Nila", "/restart", "restart"):
            self._cmd_restart()

        # 9. Default fallback
        else:
            self.send_message(
                f"🤖 I received: <i>'{clean_cmd}'</i>\n\n"
                f"Tap a button below or type:\n"
                f"• <code>/status</code> - Check hardware vitals\n"
                f"• <code>/snap</code> - Camera photo\n"
                f"• <code>/handup</code> - Raise hand (H)\n"
                f"• <code>/handdown</code> - Lower hand (G)\n"
                f"• <code>/wave</code> - Wave hand (A)\n"
                f"• <code>/restart</code> - Reboot service",
                reply_markup=self.keyboard_markup
            )

    def _cmd_menu(self):
        """Send main interactive menu"""
        help_text = (
            "🤖 <b>NILA-V2 Mission Control</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🖐️ <b>Hand Controls:</b> Raise ('H'), Lower ('G'), Wave ('A')\n"
            "📸 <b>Camera Snap:</b> Instant photo from camera\n"
            "📊 <b>System Status:</b> Mic, Speaker, Temperature, IP\n"
            "📜 <b>Recent Logs:</b> Live robot conversation & errors\n"
            "📶 <b>Wi-Fi Status:</b> Current network & signal\n"
            "🔄 <b>Restart:</b> Clean reboot of NILA"
        )
        self.send_message(help_text, reply_markup=self.keyboard_markup)

    def _cmd_hand(self, up: bool):
        """Move the robot's hand"""
        state_str = "UP" if up else "DOWN"
        if self.robot and hasattr(self.robot, "serial_controller") and self.robot.serial_controller:
            try:
                self.robot.serial_controller.move_hand(up=up)
                self.send_message(f"🖐️ <b>Hand moved {state_str}!</b> (Arduino sent '{'H' if up else 'G'}')")
            except Exception as e:
                self.send_message(f"❌ Error moving hand: {e}")
        else:
            self.send_message(f"⚠️ Serial controller not available. Hand moved {state_str} (virtual).")

    def _cmd_wave(self):
        """Wave the robot's hand (Send 'A' to Arduino)"""
        if self.robot and hasattr(self.robot, "serial_controller") and self.robot.serial_controller:
            try:
                self.robot.serial_controller.wave_hand()
                self.send_message("👋 <b>Wave sent!</b> (Arduino sent 'A')")
            except Exception as e:
                self.send_message(f"❌ Error waving hand: {e}")
        else:
            self.send_message("⚠️ Serial controller not available. Wave sent (virtual).")

    def _cmd_camera_snap(self):
        """Capture and send camera snapshot with zero lag"""
        self.send_message("📸 Snapping photo from Nila's camera...")

        jpeg_bytes = None
        if self.robot and hasattr(self.robot, "vision_service") and self.robot.vision_service:
            jpeg_bytes = self.robot.vision_service.get_latest_jpeg()

        # Fallback to web service if needed
        if not jpeg_bytes and self.robot and hasattr(self.robot, "web_service") and self.robot.web_service:
            jpeg_bytes = self.robot.web_service.get_latest_frame()

        if jpeg_bytes and len(jpeg_bytes) > 0:
            caption = f"📸 <b>NILA Camera Snapshot</b>\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
            success = self.send_photo(jpeg_bytes, caption=caption, reply_markup=self.keyboard_markup)
            if not success:
                self.send_message("❌ Failed to deliver photo to Telegram.")
        else:
            self.send_message("⚠️ Camera frame not available right now. Ensure camera is connected.")

    def _cmd_status(self):
        """Generate comprehensive system diagnostics report"""
        # 1. State
        state = "ONLINE"
        if self.robot and hasattr(self.robot, "runtime") and self.robot.runtime:
            state = getattr(self.robot.runtime, "current_state", "LISTENING")

        # 2. Mic check
        mic_ok = False
        try:
            arecord_out = subprocess.check_output("arecord -l 2>/dev/null", shell=True).decode()
            if "USB" in arecord_out or "card" in arecord_out:
                mic_ok = True
        except Exception:
            mic_ok = False

        # 3. Bluetooth Speaker check
        bt_ok = False
        mac = getattr(self.settings, "BT_SPEAKER_MAC", "41:42:84:29:F2:CE")
        try:
            bt_info = subprocess.check_output(f"bluetoothctl info {mac} 2>/dev/null", shell=True).decode()
            bt_ok = "Connected: yes" in bt_info
        except Exception:
            bt_ok = False

        # 4. Camera check
        cam_ok = False
        if self.robot and hasattr(self.robot, "vision_service") and self.robot.vision_service:
            cam_ok = self.robot.vision_service.is_running

        # 5. Pi Temp
        temp_str = "N/A"
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_c = float(f.read().strip()) / 1000.0
                temp_str = f"{temp_c:.1f}°C"
        except Exception:
            pass

        # 6. IP & Uptime
        ip = self._get_ip_address()
        uptime_sec = int(time.time() - self.start_time)
        uptime_str = f"{uptime_sec // 60}m {uptime_sec % 60}s"

        report = (
            f"📊 <b>NILA-V2 SYSTEM REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 <b>State:</b> <code>{state}</code>\n"
            f"🎤 <b>Microphone:</b> {'✅ Connected' if mic_ok else '❌ Not Found'}\n"
            f"🔊 <b>Speaker (BT):</b> {'✅ Connected' if bt_ok else '⚠️ Disconnected'}\n"
            f"📷 <b>Camera:</b> {'✅ Active' if cam_ok else '⚠️ Standby'}\n"
            f"🌡️ <b>CPU Temp:</b> <code>{temp_str}</code>\n"
            f"🌐 <b>Local IP:</b> <code>{ip}</code>\n"
            f"⏱️ <b>Uptime:</b> <code>{uptime_str}</code>\n"
        )
        self.send_message(report, reply_markup=self.keyboard_markup)

    def _cmd_logs(self):
        """Send recent logs / conversation history"""
        logs_text = ""
        # Try getting from web service logs
        if self.robot and hasattr(self.robot, "web_service") and self.robot.web_service:
            recent = self.robot.web_service.get_recent_logs()
            if recent:
                lines = []
                for item in recent[-12:]:
                    lines.append(f"[{item.get('time', '')}] {item.get('role', '').upper()}: {item.get('text', '')}")
                logs_text = "\n".join(lines)

        # Fallback to robot.log
        if not logs_text and os.path.exists("data/logs/robot.log"):
            try:
                with open("data/logs/robot.log", "r") as f:
                    all_lines = f.readlines()
                    logs_text = "".join(all_lines[-12:]).strip()
            except Exception:
                pass

        if not logs_text:
            logs_text = "No recent logs found."

        # Truncate if too long for Telegram (max 4000 chars)
        if len(logs_text) > 3500:
            logs_text = logs_text[-3500:]

        msg = f"📜 <b>Recent Robot Logs:</b>\n<pre>{logs_text}</pre>"
        self.send_message(msg, reply_markup=self.keyboard_markup)

    def _cmd_wifi(self):
        """Show current Wi-Fi status and instructions to add a new network"""
        ssid = "Unknown / Not Connected"
        signal = "N/A"
        try:
            out = subprocess.check_output("nmcli -t -f active,ssid,signal dev wifi 2>/dev/null", shell=True).decode()
            for line in out.splitlines():
                if line.startswith("yes:"):
                    parts = line.split(":")
                    if len(parts) >= 3:
                        ssid = parts[1]
                        signal = parts[2] + "%"
                    break
        except Exception:
            try:
                ssid = subprocess.check_output("iwgetid -r 2>/dev/null", shell=True).decode().strip() or ssid
            except Exception:
                pass

        ip = self._get_ip_address()
        msg = (
            f"📶 <b>WI-FI STATUS</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📡 <b>Connected SSID:</b> <code>{ssid}</code>\n"
            f"📊 <b>Signal:</b> <code>{signal}</code>\n"
            f"🌐 <b>IP Address:</b> <code>{ip}</code>\n\n"
            f"💡 <i>To connect to a new Wi-Fi:</i>\n"
            f"<code>/addwifi &lt;SSID&gt; &lt;PASSWORD&gt;</code>"
        )
        self.send_message(msg, reply_markup=self.keyboard_markup)

    def _cmd_add_wifi(self, ssid: str, password: str):
        """Connect to a new Wi-Fi using nmcli"""
        self.send_message(f"📡 Connecting to Wi-Fi <b>'{ssid}'</b>... please wait.")

        def _connect():
            try:
                cmd = f"nmcli dev wifi connect '{ssid}' password '{password}'"
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=25).decode()
                new_ip = self._get_ip_address()
                self.send_message(
                    f"✅ <b>Successfully connected to '{ssid}'!</b>\n"
                    f"🌐 New IP: <code>{new_ip}</code>"
                )
            except subprocess.CalledProcessError as e:
                err = e.output.decode() if e.output else str(e)
                self.send_message(f"❌ Failed to connect to '{ssid}':\n<code>{err}</code>")
            except Exception as e:
                self.send_message(f"❌ Wi-Fi Connection Error: {e}")

        self.executor.submit(_connect)

    def _cmd_restart(self):
        """Safely restart Nila service cleanly via systemd"""
        if getattr(self, "_is_restarting", False):
            return
        self._is_restarting = True

        self.send_message(
            "🔄 <b>Restarting NILA Service...</b>\n"
            "Please wait 5-10 seconds while Nila reboots. You will get a notification when back online!",
            reply_markup=self.keyboard_markup
        )

        def _do_restart():
            time.sleep(1.0)
            # Confirm current update so Telegram won't repeat it
            try:
                self.get_updates(offset=self.last_update_id + 1, timeout=0)
            except Exception:
                pass
            self.logger.info("🛑 Initiating clean service restart...")
            # Clean exit; systemd (Restart=always) restarts the single service cleanly
            os._exit(0)

        self.executor.submit(_do_restart)

    def _get_ip_address(self) -> str:
        """Get local network IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                out = subprocess.check_output("hostname -I", shell=True).decode().strip()
                if out:
                    return out.split()[0]
            except Exception:
                pass
        return "127.0.0.1"
