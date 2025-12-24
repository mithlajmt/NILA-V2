"""
Whisper Speech-to-Text Provider (PipeWire-compatible)
Local speech recognition with multilingual support
"""
import asyncio
import logging
import numpy as np
from typing import Optional

from src.services.speech.base_stt_provider import BaseSTTProvider, STTResult


class WhisperSTTProvider(BaseSTTProvider):
    """
    OpenAI Whisper provider for local speech recognition
    
    Accepts raw audio bytes (16-bit PCM) and converts to Whisper format
    Supports auto language detection and multilingual transcription
    """
    
    def __init__(self, model, language: Optional[str] = None):
        """
        Initialize Whisper provider
        
        Args:
            model: Loaded Whisper model (from whisper.load_model())
            language: Language code ("en", "ml", etc.) or None for auto-detect
        """
        self.model = model
        self.language = language
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"✅ Whisper provider initialized (language={language or 'auto'})")
    
    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> STTResult:
        """
        Transcribe audio using Whisper
        
        Args:
            audio_bytes: Raw audio data (16-bit PCM, 16kHz, mono)
            language: Language code or None for auto-detect
            
        Returns:
            STTResult with transcribed text and detected language
        """
        try:
            # Convert bytes to numpy array (Whisper expects float32 normalized to [-1, 1])
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Use provided language or instance default
            lang = language or self.language
            
            # Transcribe in executor (Whisper is CPU/GPU intensive)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    audio_float32,
                    language=lang,
                    fp16=False  # Use fp32 on CPU (Raspberry Pi)
                )
            )
            
            # Extract results
            text = result.get("text", "").strip()
            detected_lang = result.get("language", lang)
            
            if text:
                self.logger.info(f"✅ Whisper transcribed: '{text}' (lang={detected_lang})")
                return STTResult(
                    text=text,
                    language=detected_lang,
                    confidence=None  # Whisper doesn't provide confidence scores
                )
            else:
                self.logger.warning("⚠️ Whisper returned empty transcription")
                return STTResult(text=None, language=detected_lang, error="no_speech_detected")
                
        except Exception as e:
            self.logger.error(f"❌ Whisper transcription error: {e}")
            return STTResult(text=None, language=lang, error=f"whisper_error: {e}")
