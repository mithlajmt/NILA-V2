"""
PipeWire-compatible Speech Recognizer for Raspberry Pi
Replaces speech_recognition/PyAudio with sounddevice for stability
"""
import asyncio
import logging
import time
from typing import Optional

from src.services.speech.base_stt_provider import STTResult, BaseSTTProvider
from src.services.speech.audio_capture import AudioCapture, AudioConfig
from src.services.speech.providers.google_stt_provider import GoogleSTTProvider


class SpeechRecognizer:
    """
    Advanced speech recognition with VAD + pluggable providers (Google / Whisper)
    
    PipeWire-compatible version for Raspberry Pi with:
    - USB microphone support
    - Bluetooth audio output compatibility
    - No ALSA conflicts
    """

    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # Audio capture (replaces sr.Recognizer + sr.Microphone)
        audio_config = AudioConfig(
            sample_rate=getattr(settings, 'AUDIO_SAMPLE_RATE', 16000),
            channels=getattr(settings, 'AUDIO_CHANNELS', 1),
            vad_aggressiveness=2  # 0-3, higher = more aggressive
        )
        device_name = getattr(settings, 'AUDIO_DEVICE_NAME', "")
        self.audio_capture = AudioCapture(config=audio_config, device_name=device_name)

        # Provider selection
        self.provider_name = settings.SPEECH_PROVIDER.lower()  # "google" | "whisper" | "deepgram"
        self.provider: Optional[BaseSTTProvider] = None
        self.streaming_provider = None  # Separate streaming provider
        self.use_streaming = getattr(settings, 'DEEPGRAM_USE_STREAMING', True)
        self.last_detected_language: Optional[str] = None

        # init provider
        self._init_provider()

        self.logger.info(f"🎙️ STT ready with provider: {self.provider_name} (streaming: {self.use_streaming})")

    # ---------- provider init ----------
    def _init_provider(self):
        if self.provider_name == "whisper":
            try:
                from src.services.speech.providers.whisper_stt_provider import WhisperSTTProvider
                
                # Faster-Whisper handles its own loading
                self.provider = WhisperSTTProvider(
                    model_size=getattr(self.settings, 'WHISPER_MODEL', 'tiny'),
                    device=getattr(self.settings, 'WHISPER_DEVICE', 'cpu'),
                    compute_type="int8",  # Force int8 for Pi performance
                    language=None if self.settings.WHISPER_LANGUAGE in ("auto", "", None) else self.settings.WHISPER_LANGUAGE
                )
                self.logger.info(f"🧠 Faster-Whisper provider initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Whisper init failed: {e}. Falling back to Google.")
                self.provider_name = "google"
                self.provider = GoogleSTTProvider(default_language=getattr(self.settings, "STT_LANGUAGE", "en-IN"))
        elif self.provider_name == "deepgram":
            try:
                from src.services.speech.providers.deepgram_stt_provider import DeepgramSTTProvider
                
                # Initialize Deepgram with API key and settings
                api_key = getattr(self.settings, 'DEEPGRAM_API_KEY', '')
                if not api_key:
                    raise ValueError("DEEPGRAM_API_KEY not set in environment")
                
                # Batch provider (fallback)
                self.provider = DeepgramSTTProvider(
                    api_key=api_key,
                    model=getattr(self.settings, 'DEEPGRAM_MODEL', 'nova-2'),
                    language=getattr(self.settings, 'DEEPGRAM_LANGUAGE', 'en-US'),
                    smart_format=getattr(self.settings, 'DEEPGRAM_SMART_FORMAT', True)
                )
                
                # Streaming provider (faster!)
                if self.use_streaming:
                    try:
                        from src.services.speech.providers.deepgram_streaming_provider import DeepgramStreamingProvider
                        
                        self.streaming_provider = DeepgramStreamingProvider(
                            api_key=api_key,
                            model=getattr(self.settings, 'DEEPGRAM_MODEL', 'nova-2'),
                            language=getattr(self.settings, 'DEEPGRAM_LANGUAGE', 'en-US'),
                            smart_format=getattr(self.settings, 'DEEPGRAM_SMART_FORMAT', True),
                            interim_results=getattr(self.settings, 'DEEPGRAM_INTERIM_RESULTS', True),
                            endpointing=getattr(self.settings, 'DEEPGRAM_ENDPOINTING', 300)
                        )
                        self.logger.info(f"🚀 Deepgram STREAMING provider initialized")
                    except Exception as stream_err:
                        self.logger.warning(f"⚠️ Streaming init failed: {stream_err}. Using batch mode.")
                        self.use_streaming = False
                
                self.logger.info(f"🎙️ Deepgram provider initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Deepgram init failed: {e}. Falling back to Google.")
                self.provider_name = "google"
                self.provider = GoogleSTTProvider(default_language=getattr(self.settings, "STT_LANGUAGE", "en-IN"))
        else:
            self.provider = GoogleSTTProvider(default_language=getattr(self.settings, "STT_LANGUAGE", "en-IN"))

    # ---------- public API ----------
    async def listen(self, timeout: int = 30) -> Optional[str]:
        """
        Listen for speech and transcribe
        
        Args:
            timeout: Maximum time to wait for speech (seconds)
            
        Returns:
            Transcribed text or None if no speech detected
        """
        try:
            self.logger.info("🎯 Ready to listen...")
            
            # Capture audio (blocking call, run in executor)
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                lambda: self.audio_capture.record(
                    timeout=timeout,
                    silence_duration=1.5,
                    min_speech_duration=0.5
                )
            )
            
            if not audio_bytes:
                return None

            # Transcribe via provider
            assert self.provider is not None, "STT provider not initialized"
            result: STTResult = await self.provider.transcribe(audio_bytes)
            self.last_detected_language = result.language

            if result.text:
                print("✅ Transcribed successfully")
                return result.text
            else:
                if result.error:
                    print(f"❌ STT error: {result.error}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ listen error: {e}")
            return None

    async def listen_streaming(self, timeout: int = 30) -> Optional[str]:
        """
        Listen using STREAMING pipeline (MUCH faster!)
        
        This method:
        1. Streams audio chunks as they arrive (non-blocking)
        2. Sends to Deepgram WebSocket in real-time
        3. Gets partial results while user is speaking
        4. Returns final transcript when complete
        
        Args:
            timeout: Maximum time to wait for speech (seconds)
            
        Returns:
            Transcribed text or None if no speech detected
        """
        # Only works with streaming provider
        if not self.streaming_provider:
            self.logger.warning("⚠️ Streaming not available, falling back to batch mode")
            return await self.listen(timeout)
        
        try:
            self.logger.info("🚀 Starting streaming listen...")
            
            # Start async audio stream
            audio_stream = self.audio_capture.stream_audio(
                chunk_duration_ms=100,
                timeout=timeout,
                silence_duration=1.5,
                min_speech_duration=0.5
            )
            
            # Stream to Deepgram and collect results
            final_text = None
            partial_text = ""
            
            async for result in self.streaming_provider.stream_transcribe(audio_stream):
                if result.is_final:
                    final_text = result.text
                    self.last_detected_language = result.language
                    print(f"✅ Final: {final_text}")
                else:
                    # Show partial results (optional)
                    if result.text != partial_text:
                        partial_text = result.text
                        print(f"🔄 Partial: {partial_text}", end="\r")
            
            if final_text:
                print()  # New line after partial results
                return final_text
            else:
                self.logger.warning("⚠️ No final transcript received")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Streaming listen error: {e}")
            # Fallback to batch mode
            self.logger.info("🔄 Falling back to batch mode...")
            return await self.listen(timeout)

    def get_last_language(self) -> Optional[str]:
        """Get the language detected in the last transcription"""
        return self.last_detected_language

    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧽 Cleaning up speech recognizer...")
        # AudioCapture and providers will be garbage collected
