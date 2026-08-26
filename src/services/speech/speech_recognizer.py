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
        self.provider_name = settings.SPEECH_PROVIDER.lower()  # "google" | "whisper"
        self.provider: Optional[BaseSTTProvider] = None
        self.last_detected_language: Optional[str] = None

        # init provider
        self._init_provider()

        self.logger.info(f"🎙️ STT ready with provider: {self.provider_name}")

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
                self.provider = GoogleSTTProvider(default_language=getattr(self.settings, "STT_LANGUAGE", "ml-IN"))
        elif self.provider_name == "deepgram":
            try:
                from src.services.speech.providers.deepgram_stt_provider import DeepgramSTTProvider
                
                # Initialize Deepgram with API key and settings
                api_key = getattr(self.settings, 'DEEPGRAM_API_KEY', '')
                if not api_key:
                    raise ValueError("DEEPGRAM_API_KEY not set in environment")
                
                self.provider = DeepgramSTTProvider(
                    api_key=api_key,
                    model=getattr(self.settings, 'DEEPGRAM_MODEL', 'nova-2'),
                    language=getattr(self.settings, 'DEEPGRAM_LANGUAGE', 'en-US'),
                    smart_format=getattr(self.settings, 'DEEPGRAM_SMART_FORMAT', True)
                )
                self.logger.info(f"🎙️ Deepgram provider initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Deepgram init failed: {e}. Falling back to Google.")
                self.provider_name = "google"
                self.provider = GoogleSTTProvider(default_language=getattr(self.settings, "STT_LANGUAGE", "ml-IN"))
        else:
            self.provider = GoogleSTTProvider(default_language=getattr(self.settings, "STT_LANGUAGE", "ml-IN"))

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
                    silence_duration=0.5,
                    min_speech_duration=0.3
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

    def get_last_language(self) -> Optional[str]:
        """Get the language detected in the last transcription"""
        return self.last_detected_language

    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧽 Cleaning up speech recognizer...")
        # AudioCapture and providers will be garbage collected
