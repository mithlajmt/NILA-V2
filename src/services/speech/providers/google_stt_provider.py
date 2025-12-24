"""
Google Speech-to-Text Provider (Free Version)
Optimized for Raspberry Pi + PipeWire audio

Uses the internal Google API endpoint (same as speech_recognition)
to provide free STT without requiring Cloud credentials.
"""
import asyncio
import logging
import json
import urllib.request
import urllib.parse
from uuid import uuid4
from typing import Optional

from src.services.speech.base_stt_provider import BaseSTTProvider, STTResult


class GoogleSTTProvider(BaseSTTProvider):
    """
    Free Google STT provider using internal endpoint (no credentials needed)
    
    Compatible with PipeWire audio capture (sounddevice)
    Replicates speech_recognition.recognize_google() behavior but accepts raw bytes
    """
    
    def __init__(self, default_language: str = "en-IN"):
        self.default_language = default_language
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"✅ Google STT (Free) initialized (lang={default_language})")
    
    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> STTResult:
        """
        Transcribe audio using Google's free STT endpoint
        
        Args:
            audio_bytes: Raw audio data (16-bit PCM, 16kHz, mono)
            language: Language code (e.g., "en-IN", "ml-IN") or None for default
            
        Returns:
            STTResult with transcribed text
        """
        lang = language or self.default_language
        if lang == "auto":
            lang = "en-IN"
            
        loop = asyncio.get_event_loop()
        try:
            # Use direct HTTP request to Google's internal API
            # This logic matches what speech_recognition.recognize_google does
            text = await loop.run_in_executor(
                None,
                lambda: self._recognize_google_free(audio_bytes, lang)
            )
            
            if text:
                self.logger.info(f"✅ Transcribed: '{text}'")
                return STTResult(text=text, language=lang, confidence=None)
            else:
                return STTResult(text=None, language=lang, error="no_results")
                
        except Exception as e:
            self.logger.error(f"❌ Google STT error: {e}")
            return STTResult(text=None, language=lang, error=str(e))

    def _recognize_google_free(self, audio_data: bytes, language: str) -> Optional[str]:
        """
        Internal method to call Google's free STT API (reverse engineered)
        """
        # Convert audio bytes to FLAC could be better, but LINEAR16 is supported if we set headers right
        # However, the free endpoint really prefers FLAC. 
        # speech_recognition converts to FLAC internally.
        # Since we want to avoid complex dependencies, we can use the same endpoint 
        # but we need to match the format it expects.
        
        # NOTE: The simplest way to keep this dependency-light on Pi is to use the WAV/Linear16 method
        # but the specific Google endpoint often requires FLAC for best results.
        # Let's use the exact URL structure speech_recognition uses.
        
        try:
            # The public/internal API key used by Chrome/SpeechRecognition
            # This is public knowledge in the open source community
            key = "key=" # Removed for security, but the library uses empty or specific keys
            # Actually, speech_recognition uses standard HTTP with a specific URL
            
            url = "http://www.google.com/speech-api/v2/recognize?output=json&lang={lang}&key={key}"
            # The generic key often used in open source projects
            api_key = "PLEASE_INSERT_VALID_KEY_IF_NEEDED_BUT_DEFAULT_WORKS_OFTEN" 
            # Better approach: Use the exact logic from speech_recognition library
            
            # Let's implement a robust version that matches speech_recognition exactly
            # They convert to FLAC. To avoid pydub/ffmpeg dependency hell on Pi,
            # we will send raw PCM which is supported if Content-Type is set correctly.
            
            url = f"https://www.google.com/speech-api/v2/recognize?output=json&lang={language}&key={self._get_default_key()}"
            
            # Google's API expects FLAC usually, but some endpoints handle L16
            # If this fails, we might need to reinstall speech_recognition JUST for the API call
            # completely bypassing its microphone handling.
            
            # WAIT! The smartest move is:
            # 1. Use sounddevice for recording (Fixes Pi Issue)
            # 2. Use speech_recognition ONLY for the API call (Keeps Free STT)
            # This gives us best of both worlds without reinventing the wheel.
            
            pass 
        except Exception:
            pass
            
        # RE-EVALUATION: 
        # Writing a robust raw HTTP client for Google STT is complex (flac conversion, etc).
        # We still have `speech_recognition` installed (or can keep it just for this).
        # We can construct a `sr.AudioData` object manually from our raw bytes
        # and pass it to `sr.Recognizer().recognize_google()`.
        # This is the SAFEST and EASIEST way to keep free STT working.
        
        import speech_recognition as sr
        
        # Create AudioData from our raw bytes
        # 16000Hz, 2 bytes sample width (16-bit)
        sr_audio = sr.AudioData(audio_data, 16000, 2)
        
        recognizer = sr.Recognizer()
        return recognizer.recognize_google(sr_audio, language=language)

    def _get_default_key(self):
        return "" # Rely on internal default logic
