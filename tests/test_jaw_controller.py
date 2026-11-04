"""
Unit tests for NILA Jaw Servo Controller and Audio Lip Sync on GPIO pin 12.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from src.services.hardware.jaw_controller import JawController


class TestJawController(unittest.TestCase):
    """Tests for JawController servo mathematics, mapping, bounds, and articulation."""

    def setUp(self):
        # Reset singleton state for testing
        JawController._instance = None
        self.mock_lgpio = MagicMock()

    @patch("src.services.hardware.jaw_controller.LGPIO_AVAILABLE", True)
    @patch("src.services.hardware.jaw_controller.lgpio")
    def test_pulse_width_mapping(self, mock_lgpio):
        mock_lgpio.gpiochip_open.return_value = 1
        ctrl = JawController(
            gpio_pin=12,
            close_angle=75.0,
            max_open_angle=110.0,
        )

        # 0 degrees = 500 us
        self.assertEqual(ctrl.angle_to_pulse_us(0), 500)
        # 180 degrees = 2500 us
        self.assertEqual(ctrl.angle_to_pulse_us(180), 2500)
        # 75 degrees (closed) = 500 + (75/180) * 2000 = 1333 us
        self.assertEqual(ctrl.angle_to_pulse_us(75.0), 1333)
        # 110 degrees (max open) = 500 + (110/180) * 2000 = 1722 us
        self.assertEqual(ctrl.angle_to_pulse_us(110.0), 1722)

    @patch("src.services.hardware.jaw_controller.LGPIO_AVAILABLE", True)
    @patch("src.services.hardware.jaw_controller.lgpio")
    def test_strict_angle_clamping(self, mock_lgpio):
        """Verify jaw can never mechanically over-close (<75°) or over-open (>110°)."""
        mock_lgpio.gpiochip_open.return_value = 1
        ctrl = JawController(
            gpio_pin=12,
            close_angle=75.0,
            max_open_angle=110.0,
        )

        # Direct set_angle clamping
        ctrl.set_angle(30.0)
        self.assertEqual(ctrl._current_angle, 75.0)

        ctrl.set_angle(160.0)
        self.assertEqual(ctrl._current_angle, 110.0)

    @patch("src.services.hardware.jaw_controller.LGPIO_AVAILABLE", True)
    @patch("src.services.hardware.jaw_controller.lgpio")
    def test_sustained_speech_articulates_and_does_not_freeze_open(self, mock_lgpio):
        """
        CRITICAL TEST:
        When sustained loud voice (intensity=100) is received,
        the mouth must actively move and articulate syllables rather than freezing at 110°.
        """
        mock_lgpio.gpiochip_open.return_value = 1
        ctrl = JawController(
            gpio_pin=12,
            close_angle=75.0,
            max_open_angle=110.0,
            articulation_freq=5.0,
        )

        ctrl.set_intensity(100)
        angles_recorded = []

        # Sample angles over 300ms of sustained 100% loud speech
        for _ in range(10):
            time.sleep(0.035)
            ctrl.set_intensity(100)  # continuous 100% volume
            angles_recorded.append(ctrl._current_angle)

        ctrl.close_jaw()

        # 1. Angles must be within mechanical bounds [75.0, 110.0]
        for a in angles_recorded:
            self.assertGreaterEqual(a, 75.0)
            self.assertLessEqual(a, 110.0)

        # 2. Key check: Angles must NOT be identical/frozen!
        # There must be variation showing active syllable articulation
        min_a = min(angles_recorded)
        max_a = max(angles_recorded)
        variation = max_a - min_a
        self.assertGreater(
            variation, 8.0,
            f"Expected dynamic mouth movement on sustained speech, but angle variation was only {variation:.1f}°"
        )

    @patch("src.services.hardware.jaw_controller.LGPIO_AVAILABLE", True)
    @patch("src.services.hardware.jaw_controller.lgpio")
    def test_silence_closes_jaw(self, mock_lgpio):
        mock_lgpio.gpiochip_open.return_value = 1
        ctrl = JawController(
            gpio_pin=12,
            close_angle=75.0,
            max_open_angle=110.0,
        )

        ctrl.set_intensity(80)
        time.sleep(0.05)
        # Sound drops to 0 (silence)
        ctrl.set_intensity(0)
        time.sleep(0.4)  # wait for idle timeout

        self.assertAlmostEqual(ctrl._current_angle, 75.0, places=1)

    @patch("src.services.hardware.jaw_controller.LGPIO_AVAILABLE", True)
    @patch("src.services.hardware.jaw_controller.lgpio")
    def test_event_bus_integration(self, mock_lgpio):
        mock_lgpio.gpiochip_open.return_value = 1
        from src.core.events import SpeechAmplitudeEvent, TTSPlaybackEvent, StateChangeEvent

        ctrl = JawController(
            gpio_pin=12,
            close_angle=75.0,
            max_open_angle=110.0,
        )

        # Trigger speech amplitude event
        ctrl._on_speech_amplitude(SpeechAmplitudeEvent(intensity=90))
        time.sleep(0.05)
        self.assertGreater(ctrl._current_angle, 78.0)

        # Trigger TTS finish event -> jaw must close
        ctrl._on_tts_playback(TTSPlaybackEvent(status="finished"))
        self.assertEqual(ctrl._current_angle, 75.0)

        # Open jaw again
        ctrl.set_intensity(90)
        time.sleep(0.05)
        self.assertGreater(ctrl._current_angle, 78.0)

        # State transition to IDLE -> jaw must close
        ctrl._on_state_change(StateChangeEvent(new_state="IDLE"))
        self.assertEqual(ctrl._current_angle, 75.0)

    @patch("src.services.hardware.jaw_controller.LGPIO_AVAILABLE", True)
    @patch("src.services.hardware.jaw_controller.lgpio")
    def test_close_jaw_at_end_of_sentence_holds_closed_angle(self, mock_lgpio):
        """
        CRITICAL TEST FOR END-OF-SENTENCE JAW CLOSURE:
        When speech ends on the last sentence, close_jaw() must:
        1. Cleanly stop the articulation thread.
        2. Set and hold the closed angle (75.0°).
        3. Write 1333 µs pulse (75°) for continuous holding torque.
        4. Never leave the mouth hanging open or unpowered.
        """
        mock_lgpio.gpiochip_open.return_value = 1
        ctrl = JawController(
            gpio_pin=12,
            close_angle=75.0,
            max_open_angle=110.0,
        )

        # Simulate loud speaking at the end of a sentence
        ctrl.set_intensity(95)
        time.sleep(0.05)
        self.assertGreater(ctrl._current_angle, 75.0)

        # Last sentence ends: close_jaw() is triggered
        ctrl.close_jaw()

        # Articulation worker thread must be stopped
        if ctrl._worker_thread is not None:
            self.assertFalse(ctrl._worker_thread.is_alive())

        # Current angle must be exactly 75.0°
        self.assertEqual(ctrl._current_angle, 75.0)

        # Last pulse sent to tx_servo must be 1333 us (75.0°), NOT 0
        last_call_args = mock_lgpio.tx_servo.call_args[0]
        self.assertEqual(last_call_args[1], 12)  # GPIO 12
        self.assertEqual(last_call_args[2], 1333)  # 75° pulse width (1333 µs)

    @patch("src.services.hardware.jaw_controller.LGPIO_AVAILABLE", True)
    @patch("src.services.hardware.jaw_controller.lgpio")
    def test_idle_relax_eliminates_jitter(self, mock_lgpio):
        """
        Verify that after settling firmly at 75° under power,
        the controller detaches the servo (pulse=0) to eliminate idle PWM jitter/twitching.
        """
        mock_lgpio.gpiochip_open.return_value = 1
        ctrl = JawController(
            gpio_pin=12,
            close_angle=75.0,
            max_open_angle=110.0,
        )
        ctrl.idle_relax_delay = 0.05  # Short delay for fast test execution

        ctrl.set_intensity(90)
        time.sleep(0.02)
        ctrl.close_jaw()

        # Immediate pulse was 1333 us (powered close)
        self.assertEqual(ctrl._current_angle, 75.0)

        # After settling delay, pulse becomes 0 (relaxed/detached to stop jitter)
        time.sleep(0.08)
        last_pulse = mock_lgpio.tx_servo.call_args[0][2]
        self.assertEqual(last_pulse, 0)


if __name__ == "__main__":
    unittest.main()
