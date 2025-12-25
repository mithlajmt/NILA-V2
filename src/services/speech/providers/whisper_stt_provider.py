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
    Faster-Whisper (CTranslate2) provider for local speech recognition
    
    Optimized for Raspberry Pi 4/5:
    - Uses INT8 quantization for 4x speedup
    - Streaming-like segment processing
    """
    
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8", language: Optional[str] = None):
        """
        Initialize Faster-Whisper provider
        
        Args:
            model_size: "tiny", "base", "small", etc.
            device: "cpu" or "cuda"
            compute_type: "int8", "float16", "float32"
            language: Language code ("en", "ml", etc.) or None for auto-detect
        """
        self.language = language
        self.logger = logging.getLogger(__name__)
        
        try:
            from faster_whisper import WhisperModel
            self.logger.info(f"⏳ Loading Faster-Whisper model: '{model_size}' on {device} ({compute_type})...")
            
            # Load model (downloads automatically if needed)
            self.model = WhisperModel(
                model_size, 
                device=device, 
                compute_type=compute_type
            )
            self.logger.info(f"✅ Faster-Whisper loaded successfully!")
            
        except ImportError:
            self.logger.error("❌ 'faster-whisper' not installed. Run 'pip install faster-whisper'")
            raise
        except Exception as e:
            self.logger.error(f"❌ Failed to load model: {e}")
            raise

    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> STTResult:
        """
        Transcribe audio using Faster-Whisper
        """
        try:
            # Convert bytes to numpy array (int16 -> float32)
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Use provided language or instance default
            lang = language or self.language
            
            # Transcribe in executor (CPU intensive)
            loop = asyncio.get_event_loop()
            
            def _run_inference():
                # faster-whisper returns a generator
                segments, info = self.model.transcribe(
                    audio_float32, 
                    language=lang,
                    beam_size=5
                )
                # Consume generator to get full text
                full_text = " ".join([segment.text for segment in segments])
                return full_text.strip(), info.language
            
            text, detected_lang = await loop.run_in_executor(None, _run_inference)
            
            if text:
                self.logger.info(f"✅ Whisper transcribed: '{text}' (lang={detected_lang})")
                return STTResult(
                    text=text,
                    language=detected_lang,
                    confidence=None
                )
            else:
                self.logger.warning("⚠️ Whisper returned empty transcription")
                return STTResult(text=None, language=detected_lang, error="no_speech_detected")
                
        except Exception as e:
            self.logger.error(f"❌ Whisper transcription error: {e}")
            return STTResult(text=None, language=lang, error=f"whisper_error: {e}")
