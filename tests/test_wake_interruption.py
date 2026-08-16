"""
Unit Tests for Phase 3: Wake Detection & Interruption Lifecycle
Verifies wake word state transitions (IDLE -> LISTENING) and barge-in handling (SPEAKING -> INTERRUPTED -> LISTENING).
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus
from src.core.events import (
    Event, WakeWordDetectedEvent, SpeechInterruptedEvent, StateChangeEvent, TTSPlaybackEvent
)
from src.core.runtime import NilaRuntime
from src.core.session import SessionContext
from src.core.state import NilaState
from src.services.speech.wake_word_detector import WakeWordDetector
from src.services.tts.piper_provider import PiperTTSProvider


class MockSettings:
    WAKE_WORD_ENABLED = True
    WAKE_WORDS = "nila,hey nila"
    PIPER_BINARY_PATH = "tools/piper/piper"
    PIPER_MODEL_PATH = "data/models/piper/ml_IN-arjun-medium.onnx"
    SERIAL_PORT = "/dev/ttyUSB0"
    SERIAL_BAUD = 115200


class TestWakeInterruption(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()
        self.bus.clear()
        self.settings = MockSettings()
        self.runtime = NilaRuntime(self.settings)
        # Reset runtime state for test isolation
        self.runtime.state = NilaState.IDLE
        self.runtime.session = SessionContext()
        self.runtime.current_turn = None
        self.runtime._register_event_subscribers()

    def test_wake_detected_transitions_idle_to_listening(self):
        detector = WakeWordDetector(self.settings)
        state_changes = []

        async def state_listener(event: StateChangeEvent):
            state_changes.append(event)

        self.bus.subscribe("state.change", state_listener)

        async def run_test():
            loop = asyncio.get_running_loop()
            self.bus.set_event_loop(loop)
            
            # Emit Wake Word Event
            detector.trigger_wake(wake_word="hey nila")
            await asyncio.sleep(0.05)

        asyncio.run(run_test())

        self.assertEqual(self.runtime.state, NilaState.LISTENING)
        self.assertEqual(len(state_changes), 1)
        self.assertEqual(state_changes[0].old_state, "IDLE")
        self.assertEqual(state_changes[0].new_state, "LISTENING")

    def test_speaking_to_interrupted_to_listening(self):
        state_changes = []

        async def state_listener(event: StateChangeEvent):
            state_changes.append(event)

        self.bus.subscribe("state.change", state_listener)

        async def run_test():
            loop = asyncio.get_running_loop()
            self.bus.set_event_loop(loop)

            # Manually set state to SPEAKING
            self.runtime.state = NilaState.SPEAKING
            
            # Trigger Interruption
            self.runtime.handle_interruption(reason="User barge-in")
            await asyncio.sleep(0.05)

        asyncio.run(run_test())

        self.assertEqual(self.runtime.state, NilaState.LISTENING)
        self.assertEqual(len(state_changes), 2)
        self.assertEqual(state_changes[0].old_state, "SPEAKING")
        self.assertEqual(state_changes[0].new_state, "INTERRUPTED")
        self.assertEqual(state_changes[1].old_state, "INTERRUPTED")
        self.assertEqual(state_changes[1].new_state, "LISTENING")

    def test_piper_tts_cancellation_on_interruption(self):
        # Mock SerialController and Path to avoid hardware/file errors
        with patch("src.services.tts.piper_provider.SerialController") as mock_serial_cls, \
             patch("pathlib.Path.exists", return_value=True):
            
            mock_hardware = MagicMock()
            mock_serial_cls.return_value = mock_hardware

            provider = PiperTTSProvider(self.settings)
            provider.is_speaking = True
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            provider.current_process = mock_process

            async def run_test():
                loop = asyncio.get_running_loop()
                self.bus.set_event_loop(loop)

                # Emit SpeechInterruptedEvent
                await self.bus.publish(SpeechInterruptedEvent(reason="barge_in"))
                await asyncio.sleep(0.05)

            asyncio.run(run_test())

            # Verify speech stopped and process terminated
            self.assertFalse(provider.is_speaking)
            mock_process.terminate.assert_called_once()
            mock_hardware.send_jaw_intensity.assert_called_with(0)


if __name__ == "__main__":
    unittest.main()
