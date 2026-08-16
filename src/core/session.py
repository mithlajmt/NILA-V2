"""
NILA V2 Session & Interaction Context
Tracks multi-turn conversation sessions and per-turn scratchpad context.
"""

from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional


@dataclass
class InteractionContext:
    """Per-turn scratchpad holding state for the current interaction turn"""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    stt_transcript: Optional[str] = None
    detected_language: Optional[str] = None
    llm_response_text: Optional[str] = None
    pending_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    tts_audio_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SessionContext:
    """Session boundary tracking metadata and turn counts"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_active_at: float = field(default_factory=lambda: datetime.now().timestamp())
    user_id: str = "default_user"
    turn_count: int = 0
    active_language: str = "auto"
    metadata: Dict[str, Any] = field(default_factory=dict)
    turns: List[InteractionContext] = field(default_factory=list)

    def start_new_turn(self) -> InteractionContext:
        """Create and append a new InteractionContext turn"""
        turn = InteractionContext()
        self.turns.append(turn)
        self.turn_count += 1
        self.last_active_at = datetime.now().timestamp()
        return turn

    def get_current_turn(self) -> Optional[InteractionContext]:
        """Get the active InteractionContext turn"""
        if self.turns:
            return self.turns[-1]
        return None
