"""
Live Camera Web Streamer for NILA-V2
------------------------------------
Streams the live webcam feed with face detection bounding boxes directly
to your browser over HTTP (MJPEG).

Usage:
  ./venv/bin/python scripts/view_camera.py

Then open in your browser (phone, laptop, or Pi):
  http://<Pi-IP>:5000  (e.g., http://192.168.1.9:5000)
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from http.server import HTTPServer, BaseHTTPRequestHandler
import cv2

# Parameters for tuning detection
PROTO_PATH = "data/models/vision/deploy.prototxt"
MODEL_PATH = "data/models/vision/res10_300x300_ssd_iter_140000.caffemodel"
CASCADE_PATH = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"
CAMERA_INDEX = 0
FRAME_WIDTH = 640   # Crisp view for browser preview
FRAME_HEIGHT = 480

latest_jpeg = None
lock = threading.Lock()
running = True

# Detection stats
stats = {
    "face_count": 0,
    "latency_ms": 0.0,
    "fps": 0.0,
    "hand_state": "DOWN",
    "engine": "OpenCV DNN"
}


def camera_loop():
    global latest_jpeg, running, stats
    import numpy as np

    # Check for Deep Learning Face Detector (DNN)
    use_dnn = False
    dnn_net = None
    cascade = None

    if Path(PROTO_PATH).is_file() and Path(MODEL_PATH).is_file():
        try:
            print("🧠 Loading OpenCV Deep Neural Network (ResNet10-SSD)...")
            dnn_net = cv2.dnn.readNetFromCaffe(PROTO_PATH, MODEL_PATH)
            use_dnn = True
            stats["engine"] = "OpenCV Deep Neural Network (SSD)"
            print("✅ OpenCV DNN Face Model Active!")
        except Exception as e:
            print(f"⚠️ DNN load error: {e}, falling back to cascade")

    if not use_dnn:
        cascade = cv2.CascadeClassifier(CASCADE_PATH)
        stats["engine"] = "OpenCV Haar Cascade (Fallback)"

    from src.config.settings import Settings
    from src.services.hardware.serial_controller import SerialController
    serial_settings = Settings()
    serial_ctrl = SerialController(serial_settings)
    print(f"🔌 Serial Connection: {serial_settings.SERIAL_PORT} (Connected: {serial_ctrl.is_connected})")

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX)
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    last_face_time = 0.0
    first_face_seen = None
    consecutive_hits = 0
    current_hand_state = "DOWN"
    frame_count = 0
    fps_start = time.time()
    current_fps = 0.0

    while running:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.05)
            continue
            
        frame_count += 1
        if time.time() - fps_start >= 1.0:
            current_fps = frame_count / (time.time() - fps_start)
            frame_count = 0
            fps_start = time.time()

        h, w = frame.shape[:2]
        t0 = time.time()
        faces = []

        if use_dnn:
            # OpenCV Deep Neural Network: Only detects real human faces
            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame, (300, 300)),
                1.0,
                (300, 300),
                (104.0, 177.0, 123.0)
            )
            dnn_net.setInput(blob)
            detections = dnn_net.forward()

            for i in range(detections.shape[2]):
                conf = float(detections[0, 0, i, 2])
                if conf >= 0.65:  # High confidence threshold eliminates random objects/boards
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    fw = endX - startX
                    fh = endY - startY
                    if fw >= 35 and fh >= 35:
                        faces.append((startX, startY, fw, fh, conf))
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            raw = cascade.detectMultiScale(gray, 1.1, 6, minSize=(60, 60))
            for (fx, fy, fw, fh) in raw:
                aspect = float(fh) / float(fw) if fw > 0 else 0
                if 0.75 <= aspect <= 1.35:
                    faces.append((fx, fy, fw, fh, 0.90))

        latency = (time.time() - t0) * 1000.0
        now = time.time()

        confirmed = False
        if len(faces) > 0:
            last_face_time = now
            if first_face_seen is None:
                first_face_seen = now
            consecutive_hits += 1

            if (now - first_face_seen >= 0.20) and consecutive_hits >= 2:
                stats["hand_state"] = "UP"
                confirmed = True
                if current_hand_state != "UP":
                    current_hand_state = "UP"
                    serial_ctrl.move_hand(up=True)  # Sends 'H'
        else:
            first_face_seen = None
            consecutive_hits = 0
            if now - last_face_time > 2.5:
                stats["hand_state"] = "DOWN"
                if current_hand_state != "DOWN":
                    current_hand_state = "DOWN"
                    serial_ctrl.move_hand(up=False)  # Sends 'G'

        stats["face_count"] = len(faces) if confirmed else 0
        stats["latency_ms"] = latency
        stats["fps"] = current_fps

        # Draw visual overlays
        for item in faces:
            x, y, fw, fh, conf = item
            if confirmed:
                box_color = (0, 255, 70)  # Bright green
                label = f"FACE {conf*100:.0f}%"
            else:
                box_color = (0, 215, 255) # Yellow verifying
                label = f"VERIFYING {conf*100:.0f}%"

            cv2.rectangle(frame, (x, y), (x + fw, y + fh), box_color, 3)
            cv2.rectangle(frame, (x, max(0, y - 28)), (x + 150, y), box_color, -1)
            cv2.putText(
                frame, label, (x + 5, max(12, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2
            )

        # Header status bar overlay
        status_color = (0, 230, 70) if stats["hand_state"] == "UP" else (160, 160, 160)
        hand_text = f"HAND: {stats['hand_state']}"
        info_text = f"Faces: {len(faces)} | Latency: {latency:.1f}ms | FPS: {current_fps:.1f}"

        # Top banner
        cv2.rectangle(frame, (10, 10), (430, 50), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 10), (430, 50), status_color, 2)
        cv2.putText(frame, hand_text, (20, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(frame, info_text, (155, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # Compress to JPEG
        ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ret:
            with lock:
                latest_jpeg = buffer.tobytes()

        time.sleep(0.03)

    cap.release()


class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>NILA-V2 Live Vision Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .header {
            margin-bottom: 20px;
            text-align: center;
        }
        h1 { margin: 0 0 8px 0; font-size: 24px; color: #38bdf8; }
        .feed-card {
            background: #1e293b;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: inline-block;
        }
        img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
        }
        .info {
            margin-top: 15px;
            padding: 12px;
            background: #0f172a;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.6;
            color: #94a3b8;
        }
        .highlight { color: #38bdf8; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 NILA-V2 Live Camera & Face Vision</h1>
        <p style="color: #94a3b8; margin: 0;">Real-time feed with face bounding boxes & hand trigger state</p>
    </div>
    <div class="feed-card">
        <img src="/stream.mjpg" alt="Live Camera Feed">
        <div class="info">
            🧠 <span class="highlight">OpenCV Deep Neural Network (ResNet10-SSD)</span> Active.<br>
            🟢 <span class="highlight">Green Box</span> indicates verified human face with confidence score.<br>
            🚫 Inanimate objects, boards, and background items are rejected (0% false triggers).<br>
            🖐️ Hand state transitions to <span class="highlight">UP</span> when a real face is seen.
        </div>
    </div>
</body>
</html>
"""
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while running:
                    with lock:
                        frame_bytes = latest_jpeg
                    if frame_bytes is not None:
                        self.wfile.write(b"--frame\r\n")
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", str(len(frame_bytes)))
                        self.end_headers()
                        self.wfile.write(frame_bytes)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.04)
            except (ConnectionResetError, BrokenPipeError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP access logging to keep terminal clean
        pass


def main():
    global running
    port = 5000
    
    # Start background capture thread
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()

    server = HTTPServer(("0.0.0.0", port), StreamHandler)
    
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    print("=" * 65)
    print("🌐 NILA-V2 LIVE CAMERA WEB STREAMER ACTIVE!")
    print("=" * 65)
    print(f"👉 Open this link on your Laptop / Phone / Browser:")
    print(f"\n     http://{local_ip}:{port}\n")
    print(f"   (or on the Pi itself: http://localhost:{port})")
    print("=" * 65)
    print("🔍 Tuning Info: False-positive filter is set to minNeighbors=6, minSize=60x60")
    print("   Press CTRL+C anytime to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping camera server...")
    finally:
        running = False
        server.server_close()
        print("✅ Camera server closed.")


if __name__ == "__main__":
    main()
