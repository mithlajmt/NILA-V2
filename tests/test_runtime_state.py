"""
Unit Tests for NILA V2 Runtime State Machine & Session System
Verifies NilaState transition graph, NilaRuntime event emissions, and SessionContext tracking.
"""

import asyncio
import os
import sys
import unittest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus
from src.core.events import (
    StateChangeEvent, STTTranscriptEvent, BrainThinkingEvent, BrainLLMResponseEvent, TTSPlaybackEvent
)
from src.core.runtime import NilaRuntime
from src.core.session import SessionContext
from src.core.state import NilaState, is_valid_transition


class TestRuntimeState(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()
        self.bus.clear()
        self.runtime = NilaRuntime()
        # Reset runtime state for test isolation
        self.runtime.state = NilaState.IDLE
        self.runtime.session = SessionContext()
        self.runtime.current_turn = None
        self.runtime._register_event_subscribers()

    def test_valid_state_transitions(self):
        self.assertTrue(is_valid_transition(NilaState.IDLE, NilaState.LISTENING))
        self.assertTrue(is_valid_transition(NilaState.LISTENING, NilaState.THINKING))
        self.assertTrue(is_valid_transition(NilaState.THINKING, NilaState.EXECUTING))
        self.assertTrue(is_valid_transition(NilaState.EXECUTING, NilaState.SPEAKING))
        self.assertTrue(is_valid_transition(NilaState.SPEAKING, NilaState.IDLE))

    def test_invalid_state_transition(self):
        # Invalid direct jump: LISTENING -> EXECUTING (must go through THINKING)
        self.assertFalse(is_valid_transition(NilaState.LISTENING, NilaState.EXECUTING))
        
        # transition_to should reject invalid jump
        success = self.runtime.transition_to(NilaState.EXECUTING, reason="Invalid jump test")
        self.assertFalse(success)
        self.assertEqual(self.runtime.state, NilaState.IDLE)

    def test_state_change_event_broadcast(self):
        received_events = []

        async def state_handler(event: StateChangeEvent):
            received_events.append(event)

        self.bus.subscribe("state.change", state_handler)

        async def run_transitions():
            loop = asyncio.get_running_loop()
            self.bus.set_event_loop(loop)
            
            self.runtime.transition_to(NilaState.LISTENING, reason="User began speaking")
            await asyncio.sleep(0.05)
            
            self.runtime.transition_to(NilaState.THINKING, reason="STT complete")
            await asyncio.sleep(0.05)

        asyncio.run(run_transitions())

        self.assertEqual(len(received_events), 2)
        self.assertEqual(received_events[0].old_state, "IDLE")
        self.assertEqual(received_events[0].new_state, "LISTENING")
        self.assertEqual(received_events[1].old_state, "LISTENING")
        self.assertEqual(received_events[1].new_state, "THINKING")

    def test_session_and_interaction_context(self):
        session = self.runtime.start_new_session(user_id="test_user_123")
        self.assertEqual(session.user_id, "test_user_123")
        self.assertEqual(session.turn_count, 0)

        turn1 = self.runtime.start_turn()
        self.assertEqual(session.turn_count, 1)
        self.assertIsNotNone(turn1.turn_id)

        # Emit events and verify per-turn scratchpad capture
        asyncio.run(self.bus.publish(STTTranscriptEvent(text="Hello Nila", language="en")))
        asyncio.run(self.bus.publish(BrainLLMResponseEvent(text="Hi there!")))

        self.assertEqual(turn1.stt_transcript, "Hello Nila")
        self.assertEqual(turn1.detected_language, "en")
        self.assertEqual(turn1.llm_response_text, "Hi there!")

    def test_event_driven_state_auto_transitions(self):
        async def test_auto():
            loop = asyncio.get_running_loop()
            self.bus.set_event_loop(loop)

            # Emit thinking start
            await self.bus.publish(BrainThinkingEvent(is_thinking=True))
            await asyncio.sleep(0.05)
            self.assertEqual(self.runtime.state, NilaState.THINKING)

            # Emit TTS playback started
            await self.bus.publish(TTSPlaybackEvent(status="started"))
            await asyncio.sleep(0.05)
            self.assertEqual(self.runtime.state, NilaState.SPEAKING)

            # Emit TTS playback finished
            await self.bus.publish(TTSPlaybackEvent(status="finished"))
            await asyncio.sleep(0.05)
            self.assertEqual(self.runtime.state, NilaState.IDLE)

        asyncio.run(test_auto())


if __name__ == "__main__":
    unittest.main()
