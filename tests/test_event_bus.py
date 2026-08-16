"""
Unit Tests for NILA V2 EventBus Engine
Verifies Pub/Sub delivery, wildcard pattern matching, exception isolation, and thread safety.
"""

import asyncio
import os
import sys
import unittest
import threading
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus
from src.core.events import Event, STTTranscriptEvent, SpeechAmplitudeEvent, BrainThinkingEvent


class TestEventBus(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()
        self.bus.clear()

    def test_singleton_instance(self):
        bus2 = EventBus()
        self.assertEqual(self.bus, bus2)

    def test_exact_topic_subscription(self):
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        self.bus.subscribe("stt.transcript", handler)

        test_event = STTTranscriptEvent(text="Hello Nila", language="en")
        asyncio.run(self.bus.publish(test_event))

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].text, "Hello Nila")

    def test_wildcard_pattern_subscription(self):
        stt_events = []
        all_events = []

        async def stt_handler(event: Event):
            stt_events.append(event)

        async def global_handler(event: Event):
            all_events.append(event)

        self.bus.subscribe("stt.*", stt_handler)
        self.bus.subscribe("*", global_handler)

        event1 = STTTranscriptEvent(text="Test 1")
        event2 = SpeechAmplitudeEvent(intensity=75)

        asyncio.run(self.bus.publish(event1))
        asyncio.run(self.bus.publish(event2))

        # stt_handler should get event1
        self.assertEqual(len(stt_events), 1)
        self.assertEqual(stt_events[0].text, "Test 1")

        # global_handler should get both event1 and event2
        self.assertEqual(len(all_events), 2)

    def test_exception_isolation(self):
        called_handlers = []

        async def failing_handler(event: Event):
            raise ValueError("Simulated handler crash")

        async def safe_handler(event: Event):
            called_handlers.append(event)

        self.bus.subscribe("test.crash", failing_handler)
        self.bus.subscribe("test.crash", safe_handler)

        test_event = Event(topic="test.crash", payload="data")
        
        # Should not raise exception
        asyncio.run(self.bus.publish(test_event))

        # safe_handler must still be executed
        self.assertEqual(len(called_handlers), 1)
        self.assertEqual(called_handlers[0].payload, "data")

    def test_threadsafe_publishing(self):
        received_events = []

        async def main_test():
            loop = asyncio.get_running_loop()
            self.bus.set_event_loop(loop)

            async def handler(event: Event):
                received_events.append(event)

            self.bus.subscribe("speech.amplitude", handler)

            # Publish from background OS thread
            def background_worker():
                time.sleep(0.05)
                self.bus.publish_threadsafe(SpeechAmplitudeEvent(intensity=90))

            thread = threading.Thread(target=background_worker)
            thread.start()

            # Wait for event processing
            await asyncio.sleep(0.2)
            thread.join()

        asyncio.run(main_test())

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].intensity, 90)


if __name__ == "__main__":
    unittest.main()
