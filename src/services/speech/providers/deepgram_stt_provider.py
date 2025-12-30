"""
Deepgram Speech-to-Text Provider
High-quality, fast STT with excellent accuracy and language support

Uses Deepgram's official Python SDK for real-time and pre-recorded transcription.
Compatible with Raspberry Pi + PipeWire audio capture.
"""
import asyncio
import logging
from typing import Optional
from io import BytesIO

from src.services.speech.base_stt_provider import BaseSTTProvider, STTResult


class DeepgramSTTProvider(BaseSTTProvider):
    """
    Deepgram STT provider using official SDK
    
    Features:
    - High accuracy transcription
    - Fast processing (optimized for real-time)
    - Multi-language support
    - Smart formatting (punctuation, capitalization)
    - Confidence scores
    
    Compatible with PipeWire audio capture (sounddevice)
    Accepts raw audio bytes (16-bit PCM, 16kHz, mono)
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en-US",
        smart_format: bool = True
    ):
        """
        Initialize Deepgram STT provider
        
        Args:
            api_key: Deepgram API key
            model: Model to use ("nova-2", "enhanced", "base", "whisper")
            language: Language code (e.g., "en-US", "ml-IN") or "auto" for detection
            smart_format: Enable smart formatting (punctuation, capitalization)
        """
        self.api_key = api_key
        self.model = model
        self.language = language if language != "auto" else None
        self.smart_format = smart_format
        self.logger = logging.getLogger(__name__)
        
        # Initialize Deepgram client
        try:
            from deepgram import DeepgramClient, PrerecordedOptions
            self.DeepgramClient = DeepgramClient
            self.PrerecordedOptions = PrerecordedOptions
            
            self.client = DeepgramClient(api_key)
            self.logger.info(
                f"✅ Deepgram STT initialized (model={model}, lang={language or 'auto'})"
            )
        except ImportError:
            self.logger.error(
                "❌ Deepgram SDK not installed. Run: pip install deepgram-sdk"
            )
            raise
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Deepgram client: {e}")
            raise
    
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None
    ) -> STTResult:
        """
        Transcribe audio using Deepgram API
        
        Args:
            audio_bytes: Raw audio data (16-bit PCM, 16kHz, mono)
            language: Language code override (optional)
            
        Returns:
            STTResult with transcribed text, language, and confidence
        """
        lang = language or self.language
        
        try:
            # Configure transcription options
            options = self.PrerecordedOptions(
                model=self.model,
                smart_format=self.smart_format,
                punctuate=True,
                language=lang,
                detect_language=True if lang is None else False,
            )
            
            # Create audio source from bytes
            # Deepgram expects a dict with 'buffer' key for raw audio
            payload = {
                "buffer": audio_bytes,
            }
            
            # Perform transcription (async)
            self.logger.debug("🎯 Sending audio to Deepgram...")
            loop = asyncio.get_event_loop()
            
            # Run the synchronous Deepgram call in executor
            response = await loop.run_in_executor(
                None,
                lambda: self.client.listen.prerecorded.v("1").transcribe_file(
                    payload,
                    options
                )
            )
            
            # Extract results
            if response and hasattr(response, 'results'):
                results = response.results
                
                # Get the first channel's first alternative
                if (results.channels and 
                    len(results.channels) > 0 and
                    results.channels[0].alternatives and
                    len(results.channels[0].alternatives) > 0):
                    
                    alternative = results.channels[0].alternatives[0]
                    text = alternative.transcript.strip()
                    confidence = alternative.confidence
                    
                    # Get detected language if available
                    detected_lang = None
                    if hasattr(results, 'channels') and results.channels:
                        detected_lang = getattr(
                            results.channels[0],
                            'detected_language',
                            lang
                        )
                    
                    if text:
                        self.logger.info(f"✅ Transcribed: '{text}' (confidence: {confidence:.2f})")
                        return STTResult(
                            text=text,
                            language=detected_lang or lang,
                            confidence=confidence
                        )
                    else:
                        self.logger.warning("⚠️ Empty transcription result")
                        return STTResult(
                            text=None,
                            language=lang,
                            error="empty_result"
                        )
                else:
                    self.logger.warning("⚠️ No transcription alternatives found")
                    return STTResult(
                        text=None,
                        language=lang,
                        error="no_alternatives"
                    )
            else:
                self.logger.error("❌ Invalid response from Deepgram")
                return STTResult(
                    text=None,
                    language=lang,
                    error="invalid_response"
                )
                
        except Exception as e:
            self.logger.error(f"❌ Deepgram transcription error: {e}")
            return STTResult(
                text=None,
                language=lang,
                error=str(e)
            )
