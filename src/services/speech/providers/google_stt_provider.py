import asyncio
from typing import Optional
import speech_recognition as sr

from src.services.speech.base_stt_provider import BaseSTTProvider, STTResult

class GoogleSTTProvider(BaseSTTProvider):
    def __init__(self, recognizer: Optional[sr.Recognizer] = None, default_language: str = "en-IN"):
        self.recognizer = recognizer or sr.Recognizer()
        self.default_language = default_language

    async def transcribe(self, audio: sr.AudioData, language: Optional[str] = None) -> STTResult:
        lang = language or self.default_language
        loop = asyncio.get_event_loop()
        try:
            text = await loop.run_in_executor(
                None, lambda: self.recognizer.recognize_google(audio, language=lang, show_all=False)
            )
            return STTResult(text=text.strip(), language=lang)
        except sr.UnknownValueError:
            return STTResult(text=None, language=lang, error="no_speech_or_low_confidence")
        except sr.RequestError as e:
            return STTResult(text=None, language=lang, error=f"request_error: {e}")
        except Exception as e:
            return STTResult(text=None, language=lang, error=f"unexpected_error: {e}")
