"""
Soniox Speech-to-Text Provider (Batch Mode)
Non-streaming transcription for pre-recorded audio

Soniox offers excellent Malayalam support with 10.7% WER
(compared to Google's 42.2% and Deepgram's lack of support)
"""
import asyncio
import logging
import json
from typing import Optional

from src.services.speech.base_stt_provider import BaseSTTProvider, STTResult

try:
    import websockets
except ImportError:
    websockets = None


class SonioxSTTProvider(BaseSTTProvider):
    """
    Soniox Batch STT Provider
    
    Uses WebSocket API to transcribe complete audio files.
    Excellent for Malayalam and 60+ other languages.
    """
    
    WEBSOCKET_URL = "wss://stt-rt.soniox.com/transcribe-websocket"
    
    def __init__(
        self,
        api_key: str,
        model: str = "stt-rt-preview",
        language_hints: Optional[list] = None
    ):
        """
        Initialize Soniox batch provider
        
        Args:
            api_key: Soniox API key
            model: Model to use
            language_hints: List of language codes (e.g., ["ml", "en"])
        """
        if websockets is None:
            raise ImportError("websockets package required. Run: pip install websockets")
        
        self.api_key = api_key
        self.model = model
        self.language_hints = language_hints or ["ml", "en"]
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(
            f"✅ Soniox STT initialized (model={model}, langs={self.language_hints})"
        )
    
    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> STTResult:
        """
        Transcribe audio using Soniox
        
        Args:
            audio_bytes: Raw audio data (16-bit PCM, 16kHz, mono)
            language: Language hint (e.g., "ml" for Malayalam)
            
        Returns:
            STTResult with transcribed text
        """
        ws = None
        
        try:
            # Determine language hints
            lang_hints = self.language_hints
            if language:
                lang_hints = [language] + [l for l in self.language_hints if l != language]
            
            self.logger.info(f"🎯 Transcribing with Soniox ({len(audio_bytes)} bytes)...")
            
            # Connect to WebSocket
            ws = await websockets.connect(
                self.WEBSOCKET_URL,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Send configuration
            config = {
                "api_key": self.api_key,
                "model": self.model,
                "audio_format": "pcm_s16le",
                "sample_rate": 16000,
                "num_channels": 1,
                "language_hints": lang_hints,
                "enable_language_identification": True
            }
            
            await ws.send(json.dumps(config))
            
            # Send audio in chunks
            chunk_size = 4096
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                await ws.send(chunk)
            
            # Signal end of audio
            await ws.send(b"")
            
            # Collect results
            final_tokens = []
            detected_language = None
            
            async for message in ws:
                try:
                    response = json.loads(message)
                    
                    # Check for errors
                    if "error_code" in response:
                        error_msg = response.get("error_message", "Unknown error")
                        self.logger.error(f"❌ Soniox error: {error_msg}")
                        return STTResult(text=None, error=error_msg)
                    
                    # Check for finished
                    if response.get("finished"):
                        break
                    
                    # Collect final tokens
                    tokens = response.get("tokens", [])
                    for token in tokens:
                        if token.get("is_final"):
                            final_tokens.append(token)
                            if not detected_language and token.get("language"):
                                detected_language = token.get("language")
                                
                except json.JSONDecodeError:
                    continue
            
            # Build final text
            if final_tokens:
                text = "".join(t.get("text", "") for t in final_tokens).strip()
                avg_confidence = sum(t.get("confidence", 0) for t in final_tokens) / len(final_tokens)
                
                self.logger.info(f"✅ Transcribed: '{text}'")
                return STTResult(
                    text=text,
                    language=detected_language or lang_hints[0],
                    confidence=avg_confidence
                )
            else:
                return STTResult(text=None, error="No transcription received")
                
        except Exception as e:
            self.logger.error(f"❌ Soniox error: {e}")
            return STTResult(text=None, error=str(e))
            
        finally:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass
