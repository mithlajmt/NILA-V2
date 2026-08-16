"""
NILA V2 Wake Word Detector Service
Pluggable keyword spotting & wake detection service operating above AudioCapture.
"""

import logging
from typing import List, Optional
from src.core.event_bus import EventBus
from src.core.events import WakeWordDetectedEvent


class WakeWordDetector:
    """
    Pluggable Wake Word Detector for NILA V2.
    
    Operates above AudioCapture / VAD layer to detect keywords ("nila", "hey nila")
    and emit WakeWordDetectedEvent ("wake.detected") onto EventBus.
    """

    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.event_bus = EventBus()
        self.enabled = getattr(settings, 'WAKE_WORD_ENABLED', True)
        
        wake_words_setting = getattr(settings, 'WAKE_WORDS', 'nila,hey nila')
        if isinstance(wake_words_setting, str):
            self.wake_words = [w.strip().lower() for w in wake_words_setting.split(",") if w.strip()]
        else:
            self.wake_words = [str(w).lower() for w in wake_words_setting]

        self.logger.info(f"👂 WakeWordDetector initialized (Enabled: {self.enabled}, Target words: {self.wake_words})")

    def trigger_wake(self, wake_word: str = "nila", confidence: float = 1.0):
        """Manually or programmatically trigger a wake word event"""
        if not self.enabled:
            return

        self.logger.info(f"🗣️ WAKE WORD DETECTED: '{wake_word}' (confidence: {confidence:.2f})")
        event = WakeWordDetectedEvent(wake_word=wake_word, confidence=confidence)
        self.event_bus.publish_threadsafe(event)

    def check_transcript_for_wake(self, text: str) -> Optional[str]:
        """
        Check if a transcript contains any target wake word.
        Returns the matched wake word or None.
        """
        if not self.enabled or not text:
            return None

        text_lower = text.lower()
        for word in self.wake_words:
            if word in text_lower:
                self.trigger_wake(wake_word=word, confidence=1.0)
                return word
        return None
