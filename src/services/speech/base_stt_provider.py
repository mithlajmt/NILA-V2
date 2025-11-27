from dataclasses import dataclass
from typing import Optional, Protocol

# What every STT provider returns
@dataclass
class STTResult:
    text: Optional[str]
    language: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None

# Minimal interface all providers must implement
class BaseSTTProvider(Protocol):
    async def transcribe(self, audio, language: Optional[str] = None) -> STTResult:
        ...
