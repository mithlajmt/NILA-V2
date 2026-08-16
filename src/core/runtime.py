"""
NILA V2 Runtime Manager
Central State Machine, Session Context, and Event Integration for NILA V2.
"""

import logging
from typing import Optional
from src.core.event_bus import EventBus
from src.core.events import StateChangeEvent, STTTranscriptEvent, BrainThinkingEvent, BrainLLMResponseEvent, TTSPlaybackEvent
from src.core.session import InteractionContext, SessionContext
from src.core.state import NilaState, is_valid_transition


class NilaRuntime:
    """
    Central Runtime and State Machine Manager for NILA V2.
    
    Manages:
    - State transitions across NilaState FSM.
    - Active SessionContext and per-turn InteractionContext.
    - Broadcasting StateChangeEvent on EventBus.
    """

    _instance = None

    def __new__(cls, settings=None):
        if cls._instance is None:
            cls._instance = super(NilaRuntime, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings=None):
        if self._initialized:
            return

        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.event_bus = EventBus()
        self.state: NilaState = NilaState.IDLE
        self.session: SessionContext = SessionContext()
        self.current_turn: Optional[InteractionContext] = None
        self._initialized = True

        # Register EventBus subscribers
        self._register_event_subscribers()
        self.logger.info("🧠 NilaRuntime initialized in state: IDLE")

    def _register_event_subscribers(self):
        """Register listeners for core system events to drive state transitions"""
        self.event_bus.subscribe("stt.transcript", self._on_stt_transcript)
        self.event_bus.subscribe("brain.thinking", self._on_brain_thinking)
        self.event_bus.subscribe("brain.response", self._on_brain_response)
        self.event_bus.subscribe("tts.playback", self._on_tts_playback)
        self.event_bus.subscribe("wake.detected", self._on_wake_detected)
        self.event_bus.subscribe("speech.interrupted", self._on_speech_interrupted)

    def _on_wake_detected(self, event):
        """Handle wake word detection: IDLE or WAITING_FOR_USER -> LISTENING"""
        wake_word = getattr(event, "wake_word", "nila")
        if self.state in (NilaState.IDLE, NilaState.WAITING_FOR_USER):
            self.transition_to(NilaState.LISTENING, reason=f"Wake word '{wake_word}' detected")
        elif self.state == NilaState.SPEAKING:
            self.handle_interruption(reason=f"Wake word '{wake_word}' detected during speech")

    def _on_speech_interrupted(self, event):
        """Handle speech interruption event: SPEAKING -> INTERRUPTED -> LISTENING"""
        reason = getattr(event, "reason", "barge_in")
        self.handle_interruption(reason=reason)

    def handle_interruption(self, reason: str = "barge_in") -> bool:
        """Execute state transition flow for speech interruption (barge-in)"""
        if self.state == NilaState.SPEAKING:
            if self.transition_to(NilaState.INTERRUPTED, reason=reason):
                return self.transition_to(NilaState.LISTENING, reason="Resuming microphone capture after interruption")
        return False

    def transition_to(self, new_state: NilaState, reason: Optional[str] = None) -> bool:
        """
        Transition NILA to a new state if valid.
        Emits StateChangeEvent on EventBus.
        """
        if not is_valid_transition(self.state, new_state):
            self.logger.warning(
                f"⚠️ Invalid state transition requested: {self.state.value} -> {new_state.value} (Reason: {reason})"
            )
            return False

        old_state_str = self.state.value
        self.state = new_state
        self.logger.info(f"🔄 State Transition: {old_state_str} ➔ {new_state.value} ({reason or 'No reason provided'})")

        # Emit StateChangeEvent on EventBus
        event = StateChangeEvent(
            old_state=old_state_str,
            new_state=new_state.value,
            reason=reason,
            session_id=self.session.session_id,
            turn_id=self.current_turn.turn_id if self.current_turn else None
        )
        self.event_bus.publish_threadsafe(event)
        return True

    def start_new_session(self, user_id: str = "default_user") -> SessionContext:
        """Start a new interaction session"""
        self.session = SessionContext(user_id=user_id)
        self.current_turn = None
        self.transition_to(NilaState.IDLE, reason="New session started")
        return self.session

    def start_turn(self) -> InteractionContext:
        """Start a new per-turn interaction context"""
        self.current_turn = self.session.start_new_turn()
        return self.current_turn

    # --- EVENT SUBSCRIBER HANDLERS ---

    def _on_stt_transcript(self, event: STTTranscriptEvent):
        """Handle transcript event from STT worker"""
        if self.current_turn:
            self.current_turn.stt_transcript = event.text
            self.current_turn.detected_language = event.language

    def _on_brain_thinking(self, event: BrainThinkingEvent):
        """Handle LLM thinking state event"""
        if event.is_thinking:
            self.transition_to(NilaState.THINKING, reason="LLM inference started")

    def _on_brain_response(self, event: BrainLLMResponseEvent):
        """Handle LLM response event"""
        if self.current_turn:
            self.current_turn.llm_response_text = event.text

    def _on_tts_playback(self, event: TTSPlaybackEvent):
        """Handle TTS playback state transitions"""
        if event.status == "started":
            self.transition_to(NilaState.SPEAKING, reason="TTS audio playback started")
        elif event.status == "finished":
            self.transition_to(NilaState.IDLE, reason="TTS audio playback completed")

    def get_status_summary(self) -> str:
        """Return formatted status header for logging/console output"""
        return (
            f"State: {self.state.value} | "
            f"Session: {self.session.session_id[:8]} | "
            f"Turns: {self.session.turn_count}"
        )
