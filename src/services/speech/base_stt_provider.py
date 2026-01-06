from dataclasses import dataclass
from typing import Optional, Protocol, AsyncGenerator

# What every STT provider returns
@dataclass
class STTResult:
    text: Optional[str]
    language: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None

# Streaming result with partial/final status
@dataclass
class STTStreamResult:
    text: str
    is_final: bool  # True when sentence is complete
    confidence: float = 0.0
    language: Optional[str] = None

# Minimal interface all providers must implement
class BaseSTTProvider(Protocol):
    async def transcribe(self, audio, language: Optional[str] = None) -> STTResult:
        ...
