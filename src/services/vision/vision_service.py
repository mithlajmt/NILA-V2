"""
Vision Service for NILA-V2
Manages the isolated background vision process and publishes
VisionFaceDetectedEvent onto the NILA EventBus.
"""

import asyncio
import logging
import multiprocessing as mp
import queue
import time
from typing import Optional

from src.core.event_bus import EventBus
from src.core.events import VisionFaceDetectedEvent
from src.services.base_worker import BaseWorker
from .face_detector_process import run_face_detector_loop


class VisionService(BaseWorker):
    """
    Manages camera-based face detection in an isolated background process.
    Publishes 'vision.face' events onto the EventBus when a person is detected or leaves.
    """

    def __init__(self, settings):
        super().__init__(settings, name="VisionService")
        self.enabled = getattr(settings, "ENABLE_VISION", True)
        self.camera_index = getattr(settings, "VISION_CAMERA_INDEX", 0)
        self.width = getattr(settings, "VISION_FRAME_WIDTH", 320)
        self.height = getattr(settings, "VISION_FRAME_HEIGHT", 240)
        self.fps = getattr(settings, "VISION_FPS", 5)
        self.cooldown = getattr(settings, "VISION_COOLDOWN", 2.5)
        self.cascade_path = getattr(settings, "VISION_CASCADE_PATH", None)

        self.process: Optional[mp.Process] = None
        self.stop_event: Optional[mp.Event] = None
        self.output_queue: Optional[mp.Queue] = None
        self.consumer_task: Optional[asyncio.Task] = None
        self.is_person_present: bool = False

    def register_subscriptions(self):
        """Register any subscriptions needed by the Vision worker"""
        pass

    def start(self):
        """Start the isolated vision process and asyncio queue listener"""
        if not self.enabled:
            self.logger.info("ℹ️ Vision Service is disabled (ENABLE_VISION=False)")
            return

        if self.is_running:
            return

        self.is_running = True
        self.logger.info(f"🚀 Launching Vision Worker on CPU core (/dev/video{self.camera_index})...")

        self.stop_event = mp.Event()
        self.output_queue = mp.Queue()

        self.process = mp.Process(
            target=run_face_detector_loop,
            name="NilaVisionWorker",
            args=(
                self.stop_event,
                self.output_queue,
                self.camera_index,
                self.width,
                self.height,
                self.fps,
                self.cooldown,
                self.cascade_path
            ),
            daemon=True
        )
        self.process.start()
        self.logger.info(f"✅ Vision Process spawned (PID: {self.process.pid})")

        # Start queue polling in active asyncio loop
        try:
            loop = asyncio.get_running_loop()
            self.consumer_task = loop.create_task(self._queue_consumer_loop())
        except RuntimeError:
            self.logger.debug("No active asyncio loop during start; consumer task will start on first turn.")

    def ensure_consumer_running(self):
        """Ensure the asyncio queue consumer task is active"""
        if self.is_running and (self.consumer_task is None or self.consumer_task.done()):
            try:
                loop = asyncio.get_running_loop()
                self.consumer_task = loop.create_task(self._queue_consumer_loop())
            except RuntimeError:
                pass

    async def _queue_consumer_loop(self):
        """Non-blocking consumer loop reading events from the multiprocessing queue"""
        self.logger.debug("🔄 Vision queue consumer loop started")
        while self.is_running:
            try:
                while True:
                    try:
                        msg = self.output_queue.get_nowait()
                    except queue.Empty:
                        break

                    detected = msg.get("detected", False)
                    face_count = msg.get("count", 0)
                    latency = msg.get("latency_ms", 0.0)
                    boxes = msg.get("boxes", [])

                    self.is_person_present = detected

                    # Publish strongly-typed event
                    event = VisionFaceDetectedEvent(
                        detected=detected,
                        face_count=face_count,
                        bounding_boxes=boxes,
                        detection_latency_ms=latency
                    )
                    await self.event_bus.publish(event)

            except Exception as e:
                self.logger.error(f"❌ Error in vision queue consumer: {e}")

            await asyncio.sleep(0.08)

    def stop(self):
        """Stop the background process and clean up resources"""
        if not self.is_running:
            return

        self.is_running = False
        self.logger.info("🛑 Stopping Vision Service...")

        if self.consumer_task and not self.consumer_task.done():
            self.consumer_task.cancel()

        if self.stop_event:
            self.stop_event.set()

        if self.process and self.process.is_alive():
            self.process.join(timeout=1.5)
            if self.process.is_alive():
                self.logger.warning("⚠️ Vision process unresponsive, terminating...")
                self.process.terminate()

        self.logger.info("✅ Vision Service stopped")

    def cleanup(self):
        """Cleanup worker resources"""
        self.stop()
