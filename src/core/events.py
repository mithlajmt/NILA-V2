"""
NILA V2 Event Definitions
Strongly-typed event data classes for the Event-Driven Architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Any, Dict, Optional, Union


@dataclass
class Event:
    """Base event class for all NILA system events"""
    topic: str = "base"
    payload: Any = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


# --- SPEECH & AUDIO EVENTS ---

@dataclass
class SpeechInputEvent(Event):
    """Fired during audio capture & Voice Activity Detection (VAD)"""
    topic: str = "audio.input"
    is_speech: bool = False
    audio_bytes: Optional[bytes] = None
    sample_rate: int = 16000


@dataclass
class STTTranscriptEvent(Event):
    """Fired when Speech-to-Text provider completes transcription"""
    topic: str = "stt.transcript"
    text: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    is_final: bool = True
    error: Optional[str] = None


# --- AI BRAIN & LLM EVENTS ---

@dataclass
class BrainThinkingEvent(Event):
    """Fired when LLM inference starts or stops"""
    topic: str = "brain.thinking"
    is_thinking: bool = True


@dataclass
class BrainLLMResponseEvent(Event):
    """Fired when LLM response is generated"""
    topic: str = "brain.response"
    text: Optional[str] = None
    language_hint: Optional[str] = None
    tokens_used: int = 0
    error: Optional[str] = None


# --- TTS & VOICE EVENTS ---

@dataclass
class TTSPlaybackEvent(Event):
    """Fired during TTS audio playback state transitions"""
    topic: str = "tts.playback"
    status: str = "idle"  # "started", "playing", "finished", "error"
    file_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SpeechAmplitudeEvent(Event):
    """Fired during real-time speech amplitude analysis for jaw sync"""
    topic: str = "speech.amplitude"
    intensity: int = 0  # 0 to 100


# --- HARDWARE CONTROL EVENTS ---

@dataclass
class HardwareJawCommandEvent(Event):
    """Fired to send jaw intensity commands to Arduino"""
    topic: str = "hardware.jaw"
    intensity: int = 0  # 0 to 100


@dataclass
class HardwareGestureCommandEvent(Event):
    """Fired to command body motion animations on Arduino"""
    topic: str = "hardware.gesture"
    gesture_name: str = "idle"


# --- SYSTEM & LIFECYCLE EVENTS ---

@dataclass
class SystemStateEvent(Event):
    """Fired for application lifecycle changes"""
    topic: str = "system.state"
    state: str = "running"  # "initializing", "ready", "stopping", "shutdown", "error"
    details: Optional[str] = None


@dataclass
class StateChangeEvent(Event):
    """Fired when NilaRuntime state machine transitions state"""
    topic: str = "state.change"
    old_state: str = "IDLE"
    new_state: str = "IDLE"
    reason: Optional[str] = None
    session_id: Optional[str] = None
    turn_id: Optional[str] = None


# --- WAKE WORD & INTERRUPTION EVENTS ---

@dataclass
class WakeWordDetectedEvent(Event):
    """Fired when a wake word / hotword is detected"""
    topic: str = "wake.detected"
    wake_word: str = "nila"
    confidence: float = 1.0


@dataclass
class SpeechInterruptedEvent(Event):
    """Fired when TTS audio playback is interrupted by user speech / barge-in"""
    topic: str = "speech.interrupted"
    reason: str = "barge_in"


