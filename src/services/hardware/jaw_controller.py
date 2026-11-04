"""
Jaw Servo Controller for NILA-V2 Robot.

Controls the jaw servo motor connected directly to Raspberry Pi GPIO pin 12.
- Closed mouth angle: 75° (minimum / rest position)
- Max open mouth angle: 110° (maximum / peak volume)
- Syllable Articulation Engine: actively oscillates at natural conversational speech
  tempo (~4.3 Hz) even during sustained loud speech, preventing the mouth from
  freezing open.
- Volume sensitivity: mouth opening height scales proportionally with voice volume
  (soft voice = small subtle movements ~76°-84°; loud voice = wide dynamic movements up to 110°).
- Asymmetric analog filtering for organic mouth attack and decay.
- Automatic idle detachment to eliminate servo buzzing and heat when silent.
"""

import logging
import math
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import lgpio
    LGPIO_AVAILABLE = True
except ImportError:
    LGPIO_AVAILABLE = False
    logger.warning("⚠️ lgpio not installed. JawController will run in simulation mode.")


class JawController:
    """
    Singleton controller for the NILA robot jaw servo motor on GPIO 12.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(JawController, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        gpio_pin: int = 12,
        close_angle: float = 75.0,
        max_open_angle: float = 110.0,
        chip_num: int = 0,
        smoothing: float = 0.35,
        articulation_freq: float = 4.3,
        min_articulation_ratio: float = 0.28,
        min_pulse_us: int = 500,
        max_pulse_us: int = 2500,
        idle_timeout_sec: float = 0.35,
    ):
        if getattr(self, "_initialized", False):
            return

        self.gpio_pin = gpio_pin
        self.close_angle = float(close_angle)
        self.max_open_angle = float(max_open_angle)
        self.angle_range = self.max_open_angle - self.close_angle
        self.chip_num = chip_num
        self.smoothing = max(0.05, min(1.0, float(smoothing)))
        self.articulation_freq = float(articulation_freq)
        self.min_articulation_ratio = float(min_articulation_ratio)
        self.min_pulse_us = min_pulse_us
        self.max_pulse_us = max_pulse_us
        self.idle_timeout_sec = idle_timeout_sec

        self._current_angle = self.close_angle
        self._target_intensity = 0.0
        self._last_speech_time = 0.0
        self._speech_start_time = 0.0
        self.idle_relax_delay = 0.40  # Settle for 400ms under power, then detach to eliminate jitter

        self._gpio_handle: Optional[int] = None
        self._hw_lock = threading.Lock()
        self._relax_timer: Optional[threading.Timer] = None

        # Articulation worker thread control
        self._speech_active_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Initialize hardware
        self._init_hardware()

        # Subscribe to EventBus if available
        self._subscribe_events()

        self._initialized = True
        logger.info(
            f"👄 JawController initialized on GPIO {self.gpio_pin} "
            f"(Closed: {self.close_angle}°, Max Open: {self.max_open_angle}°, "
            f"Articulation: {self.articulation_freq}Hz)"
        )

    def _init_hardware(self):
        """Initialize lgpio handle and claim output pin."""
        if not LGPIO_AVAILABLE:
            return

        try:
            with self._hw_lock:
                self._gpio_handle = lgpio.gpiochip_open(self.chip_num)
                lgpio.gpio_claim_output(self._gpio_handle, self.gpio_pin)
                # Set initial position to closed (75°) and detach after settling to stop idle jitter
                pulse = self.angle_to_pulse_us(self.close_angle)
                lgpio.tx_servo(self._gpio_handle, self.gpio_pin, pulse)
                time.sleep(0.35)
                lgpio.tx_servo(self._gpio_handle, self.gpio_pin, 0)
                logger.info(f"✅ GPIO {self.gpio_pin} claimed for jaw servo (Chip {self.chip_num})")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize GPIO {self.gpio_pin} with lgpio: {e}")
            self._gpio_handle = None

    def _subscribe_events(self):
        """Subscribe to speech and hardware events from EventBus."""
        try:
            from src.core.event_bus import EventBus
            bus = EventBus()
            bus.subscribe("speech.amplitude", self._on_speech_amplitude)
            bus.subscribe("hardware.jaw", self._on_hardware_jaw)
            bus.subscribe("tts.playback", self._on_tts_playback)
            bus.subscribe("state.change", self._on_state_change)
        except Exception as err:
            logger.debug(f"EventBus subscription skipped: {err}")

    def _on_speech_amplitude(self, event):
        """Handle real-time speech amplitude updates."""
        intensity = getattr(event, "intensity", 0)
        self.set_intensity(intensity)

    def _on_hardware_jaw(self, event):
        """Handle direct hardware jaw command events."""
        intensity = getattr(event, "intensity", 0)
        self.set_intensity(intensity)

    def _on_tts_playback(self, event):
        """Close jaw when TTS finishes or stops."""
        status = getattr(event, "status", "")
        if status in ("finished", "error", "idle", "interrupted"):
            self.close_jaw()

    def _on_state_change(self, event):
        """Close jaw if robot transitions away from speaking."""
        new_state = getattr(event, "new_state", "")
        if new_state in ("IDLE", "LISTENING", "INTERRUPTED", "THINKING"):
            self.close_jaw()

    def angle_to_pulse_us(self, angle: float) -> int:
        """Map angle (0-180°) to microsecond pulse width (500-2500 µs)."""
        clamped = max(0.0, min(180.0, float(angle)))
        pulse = self.min_pulse_us + (clamped / 180.0) * (self.max_pulse_us - self.min_pulse_us)
        return int(round(pulse))

    def set_intensity(self, intensity: float):
        """
        Feed real-time audio volume intensity (0 to 100).
        Automatically starts the active syllable articulation loop when sound is detected.
        """
        val = 0.0 if intensity is None else float(intensity)
        now = time.time()

        if val > 8:
            # Sound detected: wake up servo and cancel any pending idle relax
            self._cancel_idle_relax()
            self._target_intensity = min(100.0, max(0.0, val))
            self._last_speech_time = now

            # If starting from silence, provide immediate opening response
            if not self._speech_active_event.is_set():
                self._speech_start_time = now
                self._speech_active_event.set()
                initial_target = self.close_angle + (self._target_intensity / 100.0) * self.angle_range * 0.6
                self._current_angle = max(self.close_angle, min(self.max_open_angle, initial_target))
                self._write_angle(self._current_angle)
                self._start_worker_if_needed()
        else:
            # Silence / between words
            self._target_intensity = 0.0

    def set_angle(self, angle: float):
        """Directly set a specific jaw angle clamped between 75° and 110°."""
        self._cancel_idle_relax()
        clamped = max(self.close_angle, min(self.max_open_angle, float(angle)))
        self._current_angle = clamped
        self._write_angle(self._current_angle)

    def close_jaw(self):
        """Immediately return jaw to closed position (75°) and schedule idle relax to eliminate jitter."""
        self._target_intensity = 0.0
        self._speech_active_event.clear()

        # Stop worker thread cleanly if running from a different thread
        worker = self._worker_thread
        if worker is not None and worker.is_alive() and threading.current_thread() != worker:
            worker.join(timeout=0.10)

        self._current_angle = self.close_angle
        self._write_angle(self.close_angle)

        # Settle firmly at 75° under power for 400ms, then detach PWM to stop idle twitching
        self._schedule_idle_relax(self.idle_relax_delay)

    def _schedule_idle_relax(self, delay_sec: float = 0.40):
        """Schedule servo detachment after settling at 75° to eliminate idle jitter."""
        with self._lock:
            if self._relax_timer is not None:
                self._relax_timer.cancel()
            self._relax_timer = threading.Timer(delay_sec, self._relax_if_idle)
            self._relax_timer.daemon = True
            self._relax_timer.start()

    def _cancel_idle_relax(self):
        """Cancel any pending relax timer when speech resumes."""
        with self._lock:
            if self._relax_timer is not None:
                self._relax_timer.cancel()
                self._relax_timer = None

    def _relax_if_idle(self):
        """Called after settling delay to cut pulses if still silent, eliminating PWM jitter."""
        if not self._speech_active_event.is_set() and self._target_intensity <= 5:
            self._relax_servo()

    def _relax_servo(self):
        """Zero the pulse width to stop sending pulses (releases servo to eliminate jitter/buzzing when idle)."""
        with self._hw_lock:
            if self._gpio_handle is not None and LGPIO_AVAILABLE:
                try:
                    lgpio.tx_servo(self._gpio_handle, self.gpio_pin, 0)
                except Exception:
                    pass

    def _start_worker_if_needed(self):
        """Launch the high-frequency articulation loop thread if not already running."""
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._worker_thread = threading.Thread(
                    target=self._articulation_loop,
                    name="JawArticulationWorker",
                    daemon=True,
                )
                self._worker_thread.start()

    def _articulation_loop(self):
        """
        High-frequency (30 Hz) articulation loop.
        Applies conversational syllable wave modulation:
        - When voice is loud: actively moves and articulates syllables between ~84° and 110°.
        - When voice is soft: subtly moves between ~76° and 83°.
        - When voice pauses or stops: smoothly closes to 75° and holds.
        - Never freezes open!
        """
        interval = 0.033  # ~30 Hz update rate

        while self._speech_active_event.is_set():
            now = time.time()

            # Check for silence or timeout
            if (now - self._last_speech_time > self.idle_timeout_sec) or (self._target_intensity <= 5):
                # Fade down to closed
                self._current_angle = 0.5 * self.close_angle + 0.5 * self._current_angle
                if abs(self._current_angle - self.close_angle) < 0.6:
                    self._current_angle = self.close_angle
                    self._write_angle(self.close_angle)
                    self._speech_active_event.clear()
                    self._schedule_idle_relax(self.idle_relax_delay)
                    break
                else:
                    self._write_angle(self._current_angle)
            else:
                # Speech is active: calculate harmonic syllable articulation wave
                elapsed = now - self._speech_start_time

                # Primary syllable rhythm (e.g. ~4.3 Hz) + secondary phonetic variation
                s1 = math.sin(2.0 * math.pi * self.articulation_freq * elapsed)
                s2 = 0.22 * math.sin(4.0 * math.pi * self.articulation_freq * elapsed)
                cycle = max(0.0, min(1.0, (s1 + s2 + 1.22) / 2.44))

                # Dynamic articulation factor: peaks at 1.0 (full volume height),
                # dips down to min_articulation_ratio (~0.28) so the mouth actively closes down on consonants
                art_factor = self.min_articulation_ratio + (1.0 - self.min_articulation_ratio) * cycle

                # Modulated intensity
                modulated_intensity = self._target_intensity * art_factor
                target_angle = self.close_angle + (modulated_intensity / 100.0) * self.angle_range

                # Asymmetric smoothing: faster opening attack, smooth articulate release
                if target_angle > self._current_angle:
                    self._current_angle = 0.65 * target_angle + 0.35 * self._current_angle
                else:
                    self._current_angle = 0.45 * target_angle + 0.55 * self._current_angle

                self._current_angle = max(
                    self.close_angle, min(self.max_open_angle, self._current_angle)
                )

                if self._speech_active_event.is_set():
                    self._write_angle(self._current_angle)

            time.sleep(interval)

        # Loop finished or cleared: enforce firm closure at 75° and schedule idle relax
        self._current_angle = self.close_angle
        self._write_angle(self.close_angle)
        self._schedule_idle_relax(self.idle_relax_delay)

    def _write_angle(self, angle: float):
        """Write microsecond servo pulse to hardware."""
        pulse_us = self.angle_to_pulse_us(angle)
        with self._hw_lock:
            if self._gpio_handle is not None and LGPIO_AVAILABLE:
                try:
                    lgpio.tx_servo(self._gpio_handle, self.gpio_pin, pulse_us)
                except Exception as e:
                    logger.debug(f"Failed to write jaw servo pulse: {e}")

    def cleanup(self):
        """Clean up GPIO resources on shutdown."""
        self._cancel_idle_relax()
        self.close_jaw()
        self._relax_servo()
        with self._hw_lock:
            if self._gpio_handle is not None and LGPIO_AVAILABLE:
                try:
                    lgpio.gpiochip_close(self._gpio_handle)
                except Exception:
                    pass
                self._gpio_handle = None
        self._initialized = False
        logger.info("👄 JawController cleaned up.")
