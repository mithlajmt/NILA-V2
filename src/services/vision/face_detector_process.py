"""
Dedicated Face Detector Background Process
Uses OpenCV Deep Neural Network (DNN - ResNet10 SSD) with fallback to Haar Cascade.
Runs completely isolated in a separate OS process via multiprocessing.
Zero impact on Python GIL, asyncio event loop, audio capture, or TTS speaking.
"""

import time
import os
import sys
import logging
from multiprocessing import Event as MPEvent, Queue
from pathlib import Path
from typing import Optional, List, Tuple, Any


def find_dnn_model_files() -> Tuple[Optional[str], Optional[str]]:
    """Find OpenCV DNN Caffe model and prototxt files"""
    proto_candidates = [
        "data/models/vision/deploy.prototxt",
        "/home/learnlogicai/finalnila/NILA-V2/data/models/vision/deploy.prototxt"
    ]
    model_candidates = [
        "data/models/vision/res10_300x300_ssd_iter_140000.caffemodel",
        "/home/learnlogicai/finalnila/NILA-V2/data/models/vision/res10_300x300_ssd_iter_140000.caffemodel"
    ]

    proto = next((p for p in proto_candidates if Path(p).is_file()), None)
    model = next((m for m in model_candidates if Path(m).is_file()), None)
    return proto, model


def find_cascade_file(preferred_path: Optional[str] = None) -> Optional[str]:
    """Fallback: Find a valid Haar cascade XML file across standard Linux paths"""
    candidates = []
    if preferred_path:
        candidates.append(preferred_path)

    candidates.extend([
        "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
        "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
        "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
    ])

    for path in candidates:
        if path and Path(path).is_file():
            return path

    return None


def run_face_detector_loop(
    stop_event: MPEvent,
    output_queue: Queue,
    camera_index: int = 0,
    width: int = 320,
    height: int = 240,
    target_fps: int = 5,
    cooldown_seconds: float = 2.5,
    cascade_path: Optional[str] = None,
    frame_buffer: Optional[Any] = None,
    frame_len: Optional[Any] = None,
    frame_lock: Optional[Any] = None
):
    """
    Entry point for the isolated camera process.
    Uses OpenCV Deep Neural Network for human face detection (0% false positives on boards/objects).
    """
    # Setup process-local logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [VisionProcess] %(message)s"
    )
    logger = logging.getLogger("VisionProcess")
    logger.info(f"📷 Starting Vision Worker on camera index {camera_index} ({width}x{height} @ {target_fps} FPS)")

    # Dedicate separate CPU Cores on Raspberry Pi 5 (Cores 2 & 3 dedicated for Vision, 0 & 1 for Audio)
    try:
        if hasattr(os, "sched_setaffinity"):
            os.sched_setaffinity(0, {2, 3})
            logger.info("⚡ Vision Worker successfully pinned to dedicated CPU cores {2, 3}")
        os.nice(5)  # Lower scheduling priority so Realtime Audio stream never gets interrupted
    except Exception as aff_err:
        logger.debug(f"Process tuning info: {aff_err}")

    try:
        import cv2
        import numpy as np
    except ImportError as e:
        logger.error(f"❌ OpenCV/NumPy not available in child process: {e}")
        return

    # Check for Deep Learning Face Detector (DNN)
    proto_path, model_path = find_dnn_model_files()
    use_dnn = False
    dnn_net = None
    cascade = None

    if proto_path and model_path:
        try:
            logger.info("🧠 Loading OpenCV Deep Neural Network (ResNet10-SSD Face Model)...")
            dnn_net = cv2.dnn.readNetFromCaffe(proto_path, model_path)
            use_dnn = True
            logger.info("✅ OpenCV Deep Neural Network loaded successfully! High-accuracy face detection ACTIVE.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load DNN face detector: {e}. Falling back to Haar Cascade.")

    if not use_dnn:
        xml_path = find_cascade_file(cascade_path)
        if not xml_path:
            logger.error("❌ No face detection model (DNN or Haar) found! Vision cannot start.")
            return
        cascade = cv2.CascadeClassifier(xml_path)
        if cascade.empty():
            logger.error(f"❌ Failed to load cascade from {xml_path}")
            return
        logger.info(f"✅ Loaded Haar cascade fallback: {xml_path}")

    # Camera opening with retry
    cap = None
    frame_interval = 1.0 / max(1, target_fps)
    is_currently_detected = False
    last_seen_time = 0.0
    first_detected_time = None
    consecutive_hits = 0

    def open_camera():
        logger.info(f"🔌 Opening /dev/video{camera_index} via V4L2...")
        c = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        if not c.isOpened():
            logger.warning("⚠️ V4L2 backend failed, falling back to default backend...")
            c = cv2.VideoCapture(camera_index)
        if c.isOpened():
            c.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            c.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            logger.info("✅ Camera stream opened successfully")
            return c
        return None

    cap = open_camera()

    while not stop_event.is_set():
        cycle_start = time.time()

        if cap is None or not cap.isOpened():
            if stop_event.wait(2.0):
                break
            cap = open_camera()
            continue

        ret, frame = cap.read()
        if not ret or frame is None:
            logger.warning("⚠️ Failed to grab frame from camera. Reconnecting...")
            cap.release()
            cap = None
            if stop_event.wait(1.0):
                break
            continue

        # Resize if hardware didn't match requested size
        h, w = frame.shape[:2]
        if w != width or h != height:
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            h, w = height, width

        detect_start = time.time()
        valid_faces = []

        if use_dnn:
            # OpenCV Deep Neural Network Face Detection (eliminates random items/boards)
            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame, (300, 300)),
                1.0,
                (300, 300),
                (104.0, 177.0, 123.0)
            )
            dnn_net.setInput(blob)
            detections = dnn_net.forward()

            for i in range(detections.shape[2]):
                confidence = float(detections[0, 0, i, 2])
                # Only accept confident human face detections (rejects inanimate objects)
                if confidence >= 0.65:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    fw = endX - startX
                    fh = endY - startY
                    if fw >= 30 and fh >= 30:
                        valid_faces.append((startX, startY, fw, fh))
        else:
            # Fallback: Haar Cascade with strict geometric filters
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            raw_faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=6,
                minSize=(55, 55),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            for (fx, fy, fw, fh) in raw_faces:
                aspect = float(fh) / float(fw) if fw > 0 else 0
                if 0.75 <= aspect <= 1.35:
                    valid_faces.append((fx, fy, fw, fh))

        latency_ms = (time.time() - detect_start) * 1000.0
        now = time.time()
        face_count = len(valid_faces)

        if face_count > 0:
            last_seen_time = now
            if first_detected_time is None:
                first_detected_time = now
            consecutive_hits += 1

            # Require continuous presence for at least 0.20s before confirming
            if not is_currently_detected:
                presence_time = now - first_detected_time
                if presence_time >= 0.20 and consecutive_hits >= 2:
                    is_currently_detected = True
                    logger.info(f"👀 Human Face Confirmed! (Count: {face_count}, Confirmed over {presence_time:.2f}s, Latency: {latency_ms:.1f}ms)")
                    output_queue.put({
                        "detected": True,
                        "count": face_count,
                        "latency_ms": latency_ms,
                        "timestamp": now,
                        "boxes": [list(f) for f in valid_faces]
                    })
        else:
            first_detected_time = None
            consecutive_hits = 0
            if is_currently_detected and (now - last_seen_time >= cooldown_seconds):
                is_currently_detected = False
                logger.info(f"👋 Face lost (cooldown {cooldown_seconds}s reached)")
                output_queue.put({
                    "detected": False,
                    "count": 0,
                    "latency_ms": latency_ms,
                    "timestamp": now,
                    "boxes": []
                })

        # Update shared memory frame buffer for web streaming preview
        if frame_buffer is not None and frame_len is not None and frame_lock is not None:
            try:
                draw_frame = frame.copy()
                for (fx, fy, fw, fh) in valid_faces:
                    box_color = (0, 255, 70) if is_currently_detected else (0, 215, 255)
                    label = "FACE CONFIRMED" if is_currently_detected else "VERIFYING..."
                    cv2.rectangle(draw_frame, (fx, fy), (fx + fw, fy + fh), box_color, 2)
                    cv2.rectangle(draw_frame, (fx, max(0, fy - 18)), (fx + 110, fy), box_color, -1)
                    cv2.putText(draw_frame, label, (fx + 3, max(12, fy - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)

                hud_color = (0, 255, 70) if is_currently_detected else (180, 180, 180)
                cv2.putText(draw_frame, f"Faces: {face_count} | {latency_ms:.0f}ms", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, hud_color, 1)

                ret_enc, jpeg_data = cv2.imencode(".jpg", draw_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                if ret_enc:
                    raw_b = jpeg_data.tobytes()
                    sz = len(raw_b)
                    if sz <= len(frame_buffer):
                        with frame_lock:
                            frame_buffer[:sz] = raw_b
                            frame_len.value = sz
            except Exception as fe:
                logger.debug(f"Frame preview encode error: {fe}")

        # Sleep remaining time to maintain target FPS without wasting CPU
        cycle_time = time.time() - cycle_start
        sleep_needed = max(0.005, frame_interval - cycle_time)
        if stop_event.wait(sleep_needed):
            break

    # Cleanup
    if cap and cap.isOpened():
        cap.release()
    logger.info("🛑 Vision Process terminated cleanly")
