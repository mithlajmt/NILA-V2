"""
NILA V2 State Machine
Defines valid runtime states and state graph transition rules.
"""

from enum import Enum
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class NilaState(str, Enum):
    """Finite State Machine states for NILA Runtime"""
    IDLE = "IDLE"                      # Resting state, waiting for trigger / wake word
    LISTENING = "LISTENING"            # Capturing microphone audio & VAD speech
    THINKING = "THINKING"              # Running LLM reasoning & generating response
    EXECUTING = "EXECUTING"            # Running tool calling / digital workflow / hardware action
    SPEAKING = "SPEAKING"              # Synthesizing & playing voice + driving jaw lip-sync
    WAITING_FOR_USER = "WAITING_FOR_USER"  # Multi-turn turn-taking window expecting continuation
    INTERRUPTED = "INTERRUPTED"        # User spoke while robot was speaking (barge-in)
    ERROR = "ERROR"                    # Recoverable fault state


# Transition graph defining valid state transitions
VALID_TRANSITIONS: Dict[NilaState, Set[NilaState]] = {
    NilaState.IDLE: {
        NilaState.LISTENING,
        NilaState.THINKING,
        NilaState.SPEAKING,
        NilaState.ERROR
    },
    NilaState.LISTENING: {
        NilaState.THINKING,
        NilaState.IDLE,
        NilaState.WAITING_FOR_USER,
        NilaState.ERROR
    },
    NilaState.THINKING: {
        NilaState.SPEAKING,
        NilaState.EXECUTING,
        NilaState.IDLE,
        NilaState.ERROR
    },
    NilaState.EXECUTING: {
        NilaState.SPEAKING,
        NilaState.THINKING,
        NilaState.IDLE,
        NilaState.ERROR
    },
    NilaState.SPEAKING: {
        NilaState.IDLE,
        NilaState.WAITING_FOR_USER,
        NilaState.LISTENING,
        NilaState.INTERRUPTED,
        NilaState.ERROR
    },
    NilaState.WAITING_FOR_USER: {
        NilaState.LISTENING,
        NilaState.IDLE,
        NilaState.ERROR
    },
    NilaState.INTERRUPTED: {
        NilaState.LISTENING,
        NilaState.IDLE,
        NilaState.ERROR
    },
    NilaState.ERROR: {
        NilaState.IDLE,
        NilaState.LISTENING
    }
}


def is_valid_transition(current_state: NilaState, next_state: NilaState) -> bool:
    """Verify if transitioning from current_state to next_state is valid"""
    if current_state == next_state:
        return True  # Re-entering same state is permitted
    allowed = VALID_TRANSITIONS.get(current_state, set())
    return next_state in allowed
