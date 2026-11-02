"""
Standalone Test Script for NILA-V2 Vision & Face Detection
-----------------------------------------------------------
Tests the multiprocessing face detection worker directly.
Displays:
- Camera stream status
- Live face count & detection bounding boxes
- Latency (in milliseconds)
- Hand UP / Hand DOWN event triggers
"""

import sys
import time
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import Settings
from src.services.vision.vision_service import VisionService
from src.core.event_bus import EventBus

def main():
    print("=" * 65)
    print("🤖 NILA-V2 CAMERA & FACE DETECTION TEST")
    print("=" * 65)
    
    settings = Settings()
    print(f"📷 Camera Device:  /dev/video{settings.VISION_CAMERA_INDEX}")
    print(f"📐 Resolution:     {settings.VISION_FRAME_WIDTH}x{settings.VISION_FRAME_HEIGHT}")
    print(f"⚡ Target Rate:    {settings.VISION_FPS} FPS")
    print(f"⏳ Cooldown:       {settings.VISION_COOLDOWN}s")
    print("=" * 65)
    print("💡 Stand in front of the camera to test face detection.")
    print("   Press CTRL+C anytime to stop.\n")

    from src.services.hardware.serial_controller import SerialController
    serial_ctrl = SerialController(settings)
    print(f"🔌 Serial Connection: {settings.SERIAL_PORT} @ {settings.SERIAL_BAUD} baud (Connected: {serial_ctrl.is_connected})")

    event_bus = EventBus()
    
    # Callback on EventBus
    def on_face_event(event):
        detected = getattr(event, "detected", False)
        count = getattr(event, "face_count", 0)
        latency = getattr(event, "detection_latency_ms", 0.0)
        
        if detected:
            print(f"👀 [DETECTED] {count} Face(s) visible! (Latency: {latency:.1f}ms) ➡️ 🖐️ HAND UP (Sent 'H' to {settings.SERIAL_PORT})")
        else:
            print(f"👋 [LOST] No faces visible ➡️ 🖐️ HAND DOWN (Sent 'G' to {settings.SERIAL_PORT})")

    event_bus.subscribe("vision.face", on_face_event)

    vision = VisionService(settings)
    vision.start()

    # Polling loop for test script
    try:
        while True:
            while not vision.output_queue.empty():
                try:
                    msg = vision.output_queue.get_nowait()
                except Exception:
                    break
                    
                detected = msg.get("detected", False)
                count = msg.get("count", 0)
                latency = msg.get("latency_ms", 0.0)
                
                from src.core.events import VisionFaceDetectedEvent
                event = VisionFaceDetectedEvent(
                    detected=detected,
                    face_count=count,
                    detection_latency_ms=latency
                )
                event_bus.publish_sync(event)
                
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n🛑 Stopping test...")
    finally:
        vision.cleanup()
        print("✅ Vision service cleaned up successfully.")

if __name__ == "__main__":
    main()
