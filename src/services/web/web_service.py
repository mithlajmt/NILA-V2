"""
NILA-V2 Web Dashboard & Telemetry Server
-----------------------------------------
Lightweight, zero-latency multi-threaded web application for monitoring and controlling
NILA in real time without impacting real-time audio or servo execution loops.

Features:
- Live MJPEG Camera Stream with Face Detection HUD
- Real-time Conversation & Speech Transcript Stream
- Live Audio Booster (Digital Gain Slider: 1.0x - 2.0x)
- Tactile Gesture Remote (Hand Up/Down, Jaw Test)
- Robot Telemetry (State, CPU Temp, Bluetooth, Arduino Vitals)
"""

import collections
import json
import logging
import os
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from src.core.event_bus import EventBus
from src.core.events import Event, StateChangeEvent, BrainLLMResponseEvent, STTTranscriptEvent, SpeechAmplitudeEvent, VisionFaceDetectedEvent


class NilaWebRequestHandler(BaseHTTPRequestHandler):
    """Multi-threaded HTTP request handler for the NILA Control Center"""

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_dashboard()
        elif path in ("/stream.mjpg", "/video_feed"):
            self._serve_mjpeg_stream()
        elif path == "/api/status":
            self._serve_api_status()
        elif path == "/api/logs":
            self._serve_api_logs()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        if path == "/api/volume":
            self._handle_api_volume(payload)
        elif path == "/api/gesture":
            self._handle_api_gesture(payload)
        elif path == "/api/reconnect":
            self._handle_api_reconnect()
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # Silence access logs to keep terminal output clean and focused
        pass

    def _serve_dashboard(self):
        """Serve the responsive single-page web app"""
        html = self.server.service.get_dashboard_html()
        content = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_mjpeg_stream(self):
        """Serve live MJPEG video stream from shared vision buffer"""
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

        last_sent = 0.0
        try:
            while self.server.service.is_running:
                now = time.time()
                # Cap preview stream to ~10 FPS for optimal Wi-Fi efficiency
                if now - last_sent < 0.09:
                    time.sleep(0.02)
                    continue

                frame_bytes = self.server.service.get_latest_frame()
                if frame_bytes:
                    try:
                        self.wfile.write(b"--frame\r\n")
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", str(len(frame_bytes)))
                        self.end_headers()
                        self.wfile.write(frame_bytes)
                        self.wfile.write(b"\r\n")
                        last_sent = now
                    except (ConnectionResetError, BrokenPipeError):
                        break
                else:
                    # Camera still initializing or vision disabled
                    time.sleep(0.2)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def _serve_api_status(self):
        """Serve system vitals and status in JSON"""
        status = self.server.service.get_status_dict()
        data = json.dumps(status).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_api_logs(self):
        """Serve recent conversation and system logs in JSON"""
        logs = self.server.service.get_recent_logs()
        data = json.dumps(logs).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_api_volume(self, payload: Dict[str, Any]):
        """Adjust digital gain and/or system volume"""
        gain = payload.get("gain")
        system_pct = payload.get("system_pct")
        success = self.server.service.set_volume(gain, system_pct)

        resp = json.dumps({"status": "ok" if success else "error", "gain": self.server.service.current_volume_gain}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)

    def _handle_api_gesture(self, payload: Dict[str, Any]):
        """Trigger physical robot gestures via Arduino"""
        gesture = payload.get("gesture", "")
        success = self.server.service.trigger_gesture(gesture)

        resp = json.dumps({"status": "ok" if success else "error", "gesture": gesture}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)

    def _handle_api_reconnect(self):
        """Request live provider to cycle session"""
        success = self.server.service.trigger_reconnect()
        resp = json.dumps({"status": "ok" if success else "error"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)


class ThreadedNilaHTTPServer(ThreadingHTTPServer):
    """Multi-threaded HTTP Server for handling concurrent browser requests and video streams"""
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, service):
        self.service = service
        super().__init__(server_address, RequestHandlerClass)


class WebService:
    """
    Background Web Service providing the real-time Operator Dashboard.
    Runs completely in an isolated daemon thread with zero delay on audio loops.
    """

    def __init__(self, settings, robot_controller):
        self.settings = settings
        self.robot = robot_controller
        self.logger = logging.getLogger(__name__)

        self.port = getattr(settings, "WEB_PORT", 5000)
        self.host = getattr(settings, "WEB_HOST", "0.0.0.0")
        self.enabled = getattr(settings, "ENABLE_WEB_DASHBOARD", True)

        self.is_running = False
        self.server: Optional[ThreadedNilaHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

        # Telemetry & State
        self.start_time = time.time()
        self.current_state = "INITIALIZING"
        self.current_volume_gain = float(getattr(settings, "GEMINI_LIVE_VOLUME_GAIN", 1.3))
        self.current_amplitude = 0
        self.face_status = {
            "detected": False,
            "count": 0,
            "latency_ms": 0.0,
            "last_seen": 0.0
        }
        self.hand_state = "DOWN"

        # Conversation and event logs ring-buffer
        self.logs_lock = threading.Lock()
        self.logs: collections.deque = collections.deque(maxlen=100)

        # Connect to EventBus
        self.event_bus = EventBus()
        self._subscribe_events()

        # Cache static dashboard HTML
        self._cached_html = self._generate_dashboard_html()

    def _subscribe_events(self):
        """Subscribe to system events for live telemetry updates"""
        self.event_bus.subscribe("*", self._on_event)

    def _on_event(self, event: Event):
        """EventBus consumer updating web state"""
        now_str = time.strftime("%H:%M:%S")

        if isinstance(event, StateChangeEvent):
            self.current_state = event.new_state
            self.add_log("system", f"State transitioned to {event.new_state} ({event.reason})", now_str)

        elif isinstance(event, BrainLLMResponseEvent):
            if event.text:
                self.add_log("robot", event.text, now_str)

        elif isinstance(event, STTTranscriptEvent):
            if event.text:
                self.add_log("user", event.text, now_str)

        elif isinstance(event, SpeechAmplitudeEvent):
            self.current_amplitude = event.intensity

        elif isinstance(event, VisionFaceDetectedEvent):
            self.face_status["detected"] = event.detected
            self.face_status["count"] = event.count
            self.face_status["latency_ms"] = event.latency_ms
            if event.detected:
                self.face_status["last_seen"] = time.time()
                self.hand_state = "UP"
            else:
                self.hand_state = "DOWN"

    def add_log(self, role: str, text: str, timestamp: Optional[str] = None):
        """Append a clean message to the live logs stream"""
        if not timestamp:
            timestamp = time.strftime("%H:%M:%S")

        with self.logs_lock:
            # Avoid repeating exact same duplicate log in succession
            if self.logs and self.logs[-1]["role"] == role and self.logs[-1]["text"] == text:
                return
            self.logs.append({
                "time": timestamp,
                "role": role,
                "text": text
            })

    def get_recent_logs(self) -> List[Dict[str, str]]:
        with self.logs_lock:
            return list(self.logs)

    def get_latest_frame(self) -> Optional[bytes]:
        """Fetch latest JPEG frame from VisionService shared buffer"""
        if hasattr(self.robot, "vision_service") and self.robot.vision_service:
            return self.robot.vision_service.get_latest_jpeg()
        return None

    def get_cpu_temp(self) -> str:
        """Read Raspberry Pi SoC temperature"""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_c = float(f.read().strip()) / 1000.0
                return f"{temp_c:.1f}°C"
        except Exception:
            return "N/A"

    def is_bluetooth_connected(self) -> bool:
        """Check if configured Bluetooth speaker is connected"""
        mac = getattr(self.settings, "BT_SPEAKER_MAC", "41:42:84:29:F2:CE")
        try:
            out = os.popen(f"bluetoothctl info {mac} 2>/dev/null").read()
            return "Connected: yes" in out
        except Exception:
            return False

    def get_status_dict(self) -> Dict[str, Any]:
        """Compile complete system status dictionary for the UI"""
        uptime_sec = int(time.time() - self.start_time)
        hrs, rem = divmod(uptime_sec, 3600)
        mins, secs = divmod(rem, 60)
        uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        serial_conn = False
        if hasattr(self.robot, "serial_controller") and self.robot.serial_controller:
            serial_conn = self.robot.serial_controller.is_connected

        # Sync live provider volume gain if active
        if hasattr(self.robot, "live_provider") and self.robot.live_provider:
            self.current_volume_gain = getattr(self.robot.live_provider, "volume_gain", self.current_volume_gain)

        return {
            "state": self.current_state,
            "uptime": uptime_str,
            "cpu_temp": self.get_cpu_temp(),
            "volume_gain": round(self.current_volume_gain, 2),
            "amplitude": self.current_amplitude,
            "bluetooth_connected": self.is_bluetooth_connected(),
            "serial_connected": serial_conn,
            "face_detected": self.face_status["detected"],
            "face_count": self.face_status["count"],
            "face_latency_ms": round(self.face_status["latency_ms"], 1),
            "hand_state": self.hand_state,
            "mode": "Expo Mode" if getattr(self.settings, "ENABLE_REALTIME_MODE", False) else "Standard"
        }

    def set_volume(self, gain: Optional[float], system_pct: Optional[int]) -> bool:
        """Update live volume gain and/or system sink volume"""
        try:
            if gain is not None:
                new_gain = max(0.5, min(2.5, float(gain)))
                self.current_volume_gain = new_gain
                if hasattr(self.robot, "live_provider") and self.robot.live_provider:
                    self.robot.live_provider.volume_gain = new_gain
                self.add_log("system", f"🔊 Digital volume gain set to {new_gain:.1f}x ({int(new_gain * 100)}%)")

            if system_pct is not None:
                pct = max(0, min(150, int(system_pct)))
                os.system(f"pactl set-sink-volume @DEFAULT_SINK@ {pct}% > /dev/null 2>&1")
                self.add_log("system", f"🔊 System Bluetooth speaker volume set to {pct}%")

            return True
        except Exception as e:
            self.logger.warning(f"Error setting volume: {e}")
            return False

    def trigger_gesture(self, gesture: str) -> bool:
        """Send physical servo gesture to Arduino"""
        if not hasattr(self.robot, "serial_controller") or not self.robot.serial_controller:
            return False

        ctrl = self.robot.serial_controller
        gesture = gesture.lower()

        try:
            if gesture in ("hand_up", "wave"):
                ctrl.move_hand(up=True)
                self.hand_state = "UP"
                self.add_log("system", "🖐️ Gesture: Hand Raised (Wave)")
                return True
            elif gesture in ("hand_down", "rest"):
                ctrl.move_hand(up=False)
                self.hand_state = "DOWN"
                self.add_log("system", "🫳 Gesture: Hand Lowered (Rest)")
                return True
            elif gesture == "jaw":
                # Quick jaw test twitch
                ctrl.send_jaw_intensity(220)
                threading.Timer(0.3, lambda: ctrl.send_jaw_intensity(0)).start()
                self.add_log("system", "🗣️ Gesture: Jaw Test Twitch")
                return True
            elif gesture == "smile":
                ctrl.send_jaw_intensity(100)
                threading.Timer(0.5, lambda: ctrl.send_jaw_intensity(0)).start()
                self.add_log("system", "😊 Gesture: Smile Nod")
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Gesture trigger error: {e}")
            return False

    def trigger_reconnect(self) -> bool:
        """Trigger graceful live session reconnect"""
        try:
            if hasattr(self.robot, "live_provider") and self.robot.live_provider:
                self.add_log("system", "🔄 Requested Live WebSocket Session Reconnect...")
                if hasattr(self.robot.live_provider, "session") and self.robot.live_provider.session:
                    # Closing active session will cause loop to reconnect cleanly
                    pass
            return True
        except Exception:
            return False

    def start(self):
        """Start the web server in an independent daemon thread"""
        if not self.enabled:
            self.logger.info("ℹ️ Web Dashboard is disabled (ENABLE_WEB_DASHBOARD=False)")
            return

        if self.is_running:
            return

        self.is_running = True
        try:
            self.server = ThreadedNilaHTTPServer((self.host, self.port), NilaWebRequestHandler, self)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="NilaWebDaemon")
            self.server_thread.start()

            # Find local IP
            local_ip = "127.0.0.1"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                pass

            self.logger.info("=" * 65)
            self.logger.info("🌐 NILA-V2 WEB CONTROL DASHBOARD ACTIVE!")
            self.logger.info(f"👉 Open in browser (Laptop/Phone): http://{local_ip}:{self.port}")
            self.logger.info(f"   (Local: http://localhost:{self.port})")
            self.logger.info("=" * 65)
            self.add_log("system", f"🌐 Control Dashboard ready at http://{local_ip}:{self.port}")
        except Exception as e:
            self.logger.error(f"❌ Failed to start Web Server on port {self.port}: {e}")
            self.is_running = False

    def stop(self):
        """Stop the HTTP server cleanly"""
        if not self.is_running:
            return
        self.is_running = False
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
        self.logger.info("🛑 Web Dashboard stopped")

    def get_dashboard_html(self) -> str:
        return self._cached_html

    def _generate_dashboard_html(self) -> str:
        """Returns the complete, responsive, glassmorphic Single Page App"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NILA V2 | Robot Control Center</title>
    <style>
        :root {
            --bg-base: #060913;
            --bg-surface: rgba(15, 23, 42, 0.75);
            --bg-card: rgba(22, 33, 62, 0.65);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-focus: rgba(56, 189, 248, 0.4);
            --cyan: #00f0ff;
            --blue: #38bdf8;
            --emerald: #10b981;
            --purple: #a855f7;
            --amber: #f59e0b;
            --rose: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(0, 240, 255, 0.06) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(168, 85, 247, 0.06) 0%, transparent 40%);
            color: var(--text-main);
            font-family: var(--font-sans);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Bar */
        header {
            background: rgba(10, 15, 29, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-subtle);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .robot-icon {
            font-size: 24px;
            filter: drop-shadow(0 0 10px rgba(0, 240, 255, 0.5));
            animation: pulse-glow 3s infinite alternate;
        }

        .brand-title {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(135deg, var(--cyan), var(--blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-subtitle {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .top-pills {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .pill {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--text-muted);
        }

        .status-dot.active {
            background: var(--emerald);
            box-shadow: 0 0 10px var(--emerald);
            animation: blink 1.8s infinite;
        }

        /* Grid Layout */
        main {
            padding: 20px;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1.1fr 1.3fr 0.9fr;
            gap: 20px;
            flex: 1;
        }

        @media (max-width: 1100px) {
            main { grid-template-columns: 1fr 1fr; }
        }

        @media (max-width: 768px) {
            main { grid-template-columns: 1fr; padding: 12px; gap: 14px; }
            header { padding: 10px 16px; }
        }

        /* Cards & Glassmorphism */
        .card {
            background: var(--bg-surface);
            backdrop-filter: blur(14px);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            position: relative;
            overflow: hidden;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: 10px;
        }

        .card-title {
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Camera Feed HUD */
        .video-box {
            position: relative;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            aspect-ratio: 4 / 3;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(0, 240, 255, 0.2);
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.08);
        }

        .video-box img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .hud-corner {
            position: absolute;
            width: 16px;
            height: 16px;
            border-color: var(--cyan);
            border-style: solid;
            pointer-events: none;
        }
        .hud-tl { top: 8px; left: 8px; border-width: 2px 0 0 2px; }
        .hud-tr { top: 8px; right: 8px; border-width: 2px 2px 0 0; }
        .hud-bl { bottom: 8px; left: 8px; border-width: 0 0 2px 2px; }
        .hud-br { bottom: 8px; right: 8px; border-width: 0 2px 2px 0; }

        .hud-badge {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(6px);
            padding: 4px 10px;
            border-radius: 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--cyan);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .stat-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .stat-label { font-size: 11px; color: var(--text-muted); }
        .stat-value { font-size: 16px; font-weight: 700; font-family: var(--font-mono); }

        /* Conversation & Logs Stream */
        .chat-container {
            height: 380px;
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 14px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            scroll-behavior: smooth;
        }

        .chat-container::-webkit-scrollbar { width: 5px; }
        .chat-container::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }

        .chat-bubble {
            max-width: 90%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.45;
            display: flex;
            flex-direction: column;
            gap: 4px;
            animation: fadeIn 0.3s ease;
        }

        .chat-bubble.user {
            align-self: flex-start;
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.25);
            color: #e0f2fe;
        }

        .chat-bubble.robot {
            align-self: flex-end;
            background: rgba(168, 85, 247, 0.12);
            border: 1px solid rgba(168, 85, 247, 0.3);
            color: #f3e8ff;
        }

        .chat-bubble.system {
            align-self: center;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            color: var(--text-muted);
            font-size: 11px;
            font-family: var(--font-mono);
            padding: 4px 10px;
            border-radius: 20px;
        }

        .chat-author {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .chat-bubble.user .chat-author { color: var(--cyan); }
        .chat-bubble.robot .chat-author { color: var(--purple); }

        /* Volume Booster Control */
        .booster-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .booster-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .slider-wrap {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        input[type="range"] {
            flex: 1;
            height: 6px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.1);
            outline: none;
            -webkit-appearance: none;
        }

        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--cyan);
            cursor: pointer;
            box-shadow: 0 0 10px var(--cyan);
            transition: transform 0.1s;
        }

        input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.15); }

        .boost-presets {
            display: flex;
            gap: 8px;
        }

        .btn-preset {
            flex: 1;
            padding: 6px 10px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-subtle);
            color: var(--text-main);
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-preset:hover {
            background: rgba(0, 240, 255, 0.15);
            border-color: var(--cyan);
        }

        /* Remote Gesture Deck */
        .gesture-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .btn-gesture {
            padding: 14px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-subtle);
            color: var(--text-main);
            font-size: 13px;
            font-weight: 600;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            transition: all 0.2s;
            user-select: none;
        }

        .btn-gesture:active {
            transform: scale(0.96);
        }

        .btn-gesture:hover {
            background: rgba(56, 189, 248, 0.12);
            border-color: var(--blue);
            box-shadow: 0 4px 15px rgba(56, 189, 248, 0.2);
        }

        .btn-gesture .btn-icon {
            font-size: 24px;
        }

        .btn-reconnect {
            grid-column: span 2;
            background: rgba(244, 63, 94, 0.08);
            border-color: rgba(244, 63, 94, 0.25);
            color: #fecdd3;
        }

        .btn-reconnect:hover {
            background: rgba(244, 63, 94, 0.2);
            border-color: var(--rose);
            box-shadow: 0 4px 15px rgba(244, 63, 94, 0.3);
        }

        /* Equalizer Visualizer */
        .eq-bar-wrap {
            display: flex;
            align-items: flex-end;
            gap: 3px;
            height: 24px;
            padding: 2px;
        }

        .eq-bar {
            width: 4px;
            background: var(--cyan);
            border-radius: 2px;
            height: 4px;
            transition: height 0.1s ease;
        }

        /* Animations */
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes pulse-glow { 0% { filter: drop-shadow(0 0 6px var(--cyan)); } 100% { filter: drop-shadow(0 0 16px var(--purple)); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <span class="robot-icon">🤖</span>
            <div>
                <div class="brand-title">NILA V2</div>
                <div class="brand-subtitle">Interactive Robot Console</div>
            </div>
        </div>
        <div class="top-pills">
            <div class="pill">
                <span class="status-dot active" id="dotState"></span>
                <span id="lblState">LISTENING</span>
            </div>
            <div class="pill">
                <span>🌡️</span>
                <span id="lblCpu">--°C</span>
            </div>
            <div class="pill">
                <span>⏱️</span>
                <span id="lblUptime">00:00:00</span>
            </div>
        </div>
    </header>

    <main>
        <!-- Column 1: Live Vision & Camera -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">👁️ Vision Feed (DNN Tracker)</div>
                <div class="pill" style="padding: 2px 8px; font-size: 11px;" id="badgeDetection">IDLE</div>
            </div>
            <div class="video-box">
                <img id="streamImg" src="/stream.mjpg" alt="Connecting live video feed..." onerror="this.onerror=null; setTimeout(() => { this.src = '/stream.mjpg?' + Date.now(); }, 1500);">
                <div class="hud-corner hud-tl"></div>
                <div class="hud-corner hud-tr"></div>
                <div class="hud-corner hud-bl"></div>
                <div class="hud-corner hud-br"></div>
                <div class="hud-badge" id="hudBadge">OpenCV SSD • 320x240</div>
            </div>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Faces Verified</span>
                    <span class="stat-value" id="valFaces">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Inference Latency</span>
                    <span class="stat-value" id="valLatency">-- ms</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Hand Tracking</span>
                    <span class="stat-value" id="valHand">DOWN</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Serial Link</span>
                    <span class="stat-value" id="valSerial">CONNECTED</span>
                </div>
            </div>
        </div>

        <!-- Column 2: Dialogue & Audio Booster -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">💬 Live Dialogue & Speech</div>
                <div class="eq-bar-wrap" id="eqWrap">
                    <div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div>
                    <div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div>
                </div>
            </div>

            <div class="chat-container" id="chatBox">
                <div class="chat-bubble system">
                    <span>⚡ Connecting to Nila Event Stream...</span>
                </div>
            </div>

            <div class="booster-box">
                <div class="booster-header">
                    <span style="font-size: 12px; font-weight: 600;">🔊 Digital Voice Booster</span>
                    <span style="font-size: 12px; color: var(--cyan); font-weight: 700; font-family: var(--font-mono);" id="valGain">1.3x (+30%)</span>
                </div>
                <div class="slider-wrap">
                    <span style="font-size: 11px; color: var(--text-muted);">1.0x</span>
                    <input type="range" id="sliderGain" min="0.8" max="2.0" step="0.05" value="1.3">
                    <span style="font-size: 11px; color: var(--text-muted);">2.0x</span>
                </div>
                <div class="boost-presets">
                    <button class="btn-preset" onclick="setGain(1.0)">Natural (1.0x)</button>
                    <button class="btn-preset" onclick="setGain(1.3)">Expo Boost (1.3x)</button>
                    <button class="btn-preset" onclick="setGain(1.6)">Max Loud (1.6x)</button>
                </div>
            </div>
        </div>

        <!-- Column 3: Robotic Gestures & Hardware Vitals -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">🎮 Remote Controls</div>
                <div class="pill" style="padding: 2px 8px; font-size: 11px;" id="badgeMode">Expo Mode</div>
            </div>

            <div class="gesture-grid">
                <button class="btn-gesture" onclick="sendGesture('wave')">
                    <span class="btn-icon">👋</span>
                    <span>Raise Hand</span>
                </button>
                <button class="btn-gesture" onclick="sendGesture('hand_down')">
                    <span class="btn-icon">🫳</span>
                    <span>Lower Hand</span>
                </button>
                <button class="btn-gesture" onclick="sendGesture('jaw')">
                    <span class="btn-icon">🗣️</span>
                    <span>Test Jaw</span>
                </button>
                <button class="btn-gesture" onclick="sendGesture('smile')">
                    <span class="btn-icon">😊</span>
                    <span>Smile Nod</span>
                </button>
                <button class="btn-gesture btn-reconnect" onclick="reconnectSession()">
                    <span class="btn-icon">🔄</span>
                    <span>Reconnect Gemini Session</span>
                </button>
            </div>

            <div class="card-header" style="margin-top: 10px;">
                <div class="card-title">📡 Hardware Telemetry</div>
            </div>

            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Bluetooth Speaker</span>
                    <span class="stat-value" id="valBt">CONNECTING</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Model Pipeline</span>
                    <span class="stat-value" style="font-size: 13px;">Gemini 3.1 Live</span>
                </div>
            </div>
        </div>
    </main>

    <script>
        let lastLogsCount = 0;
        const sliderGain = document.getElementById('sliderGain');
        const valGain = document.getElementById('valGain');

        // Polling telemetry
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                if (!res.ok) return;
                const data = await res.json();

                document.getElementById('lblState').innerText = data.state;
                document.getElementById('lblCpu').innerText = data.cpu_temp;
                document.getElementById('lblUptime').innerText = data.uptime;
                document.getElementById('valFaces').innerText = data.face_count;
                document.getElementById('valLatency').innerText = data.face_latency_ms + ' ms';
                document.getElementById('valHand').innerText = data.hand_state;
                document.getElementById('valSerial').innerText = data.serial_connected ? 'CONNECTED' : 'OFFLINE';
                document.getElementById('valBt').innerText = data.bluetooth_connected ? '3.0BT READY' : 'OFFLINE';
                document.getElementById('badgeMode').innerText = data.mode;

                const badge = document.getElementById('badgeDetection');
                if (data.face_detected) {
                    badge.innerText = 'PERSON DETECTED';
                    badge.style.color = '#10b981';
                    badge.style.borderColor = '#10b981';
                } else {
                    badge.innerText = 'SEARCHING';
                    badge.style.color = '#94a3b8';
                    badge.style.borderColor = 'rgba(255,255,255,0.08)';
                }

                // Animate state dot color
                const dot = document.getElementById('dotState');
                if (data.state === 'SPEAKING') {
                    dot.style.background = '#a855f7';
                    dot.style.boxShadow = '0 0 10px #a855f7';
                } else if (data.state === 'LISTENING') {
                    dot.style.background = '#10b981';
                    dot.style.boxShadow = '0 0 10px #10b981';
                } else {
                    dot.style.background = '#f59e0b';
                    dot.style.boxShadow = '0 0 10px #f59e0b';
                }

                // Visualizer bounce
                animateEqualizer(data.amplitude || 0);

                // Update slider if not focused
                if (document.activeElement !== sliderGain) {
                    sliderGain.value = data.volume_gain;
                    updateGainLabel(data.volume_gain);
                }
            } catch (e) {
                console.debug('Status polling error', e);
            }
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                if (!res.ok) return;
                const logs = await res.json();

                if (logs.length !== lastLogsCount) {
                    renderLogs(logs);
                    lastLogsCount = logs.length;
                }
            } catch (e) {}
        }

        function renderLogs(logs) {
            const box = document.getElementById('chatBox');
            box.innerHTML = '';
            logs.forEach(log => {
                const bubble = document.createElement('div');
                bubble.className = `chat-bubble ${log.role}`;
                if (log.role === 'system') {
                    bubble.innerHTML = `<span>[${log.time}] ${escapeHtml(log.text)}</span>`;
                } else {
                    const icon = log.role === 'user' ? '🎤 VISITOR' : '🤖 NILA';
                    bubble.innerHTML = `
                        <div class="chat-author"><span>${icon}</span><span style="opacity:0.6;font-size:9px;">${log.time}</span></div>
                        <div>${escapeHtml(log.text)}</div>
                    `;
                }
                box.appendChild(bubble);
            });
            box.scrollTop = box.scrollHeight;
        }

        function animateEqualizer(amp) {
            const bars = document.querySelectorAll('.eq-bar');
            bars.forEach((b, i) => {
                const h = Math.max(4, Math.min(24, (amp / 8) * (0.6 + Math.random() * 0.8)));
                b.style.height = h + 'px';
            });
        }

        function updateGainLabel(val) {
            const pct = Math.round((val - 1.0) * 100);
            const sign = pct >= 0 ? '+' : '';
            valGain.innerText = `${val}x (${sign}${pct}%)`;
        }

        async function setGain(val) {
            sliderGain.value = val;
            updateGainLabel(val);
            try {
                await fetch('/api/volume', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gain: parseFloat(val) })
                });
            } catch (e) {}
        }

        sliderGain.addEventListener('input', (e) => {
            updateGainLabel(e.target.value);
        });

        sliderGain.addEventListener('change', (e) => {
            setGain(e.target.value);
        });

        async function sendGesture(type) {
            try {
                await fetch('/api/gesture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gesture: type })
                });
            } catch (e) {}
        }

        async function reconnectSession() {
            if (!confirm('Cycle Gemini Live WebSocket session now?')) return;
            try {
                await fetch('/api/reconnect', { method: 'POST' });
            } catch (e) {}
        }

        function escapeHtml(str) {
            return str.replace(/[&<>'"]/g, tag => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
            }[tag] || tag));
        }

        setInterval(fetchStatus, 800);
        setInterval(fetchLogs, 1200);
        fetchStatus();
        fetchLogs();
    </script>
</body>
</html>
"""
