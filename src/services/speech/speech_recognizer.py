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
            vad_aggressiveness=1  # 0-3, higher = more aggressive
        )
        device_name = getattr(settings, 'AUDIO_DEVICE_NAME', "")
        self.audio_capture = AudioCapture(config=audio_config, device_name=device_name)

        # Provider selection
        self.provider_name = settings.SPEECH_PROVIDER.lower()  # "google" | "whisper" | "deepgram" | "soniox"
        self.provider: Optional[BaseSTTProvider] = None
        self.streaming_provider = None  # Separate streaming provider
        self.use_streaming = getattr(settings, 'STT_USE_STREAMING', True)
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
        elif self.provider_name in ("deepgram", "deepgram-streaming"):
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
        
        elif self.provider_name in ("soniox", "soniox-streaming"):
            try:
                from src.services.speech.providers.soniox_stt_provider import SonioxSTTProvider
                
                # Initialize Soniox with API key and settings
                api_key = getattr(self.settings, 'SONIOX_API_KEY', '')
                if not api_key:
                    raise ValueError("SONIOX_API_KEY not set in environment")
                
                # Parse language hints from comma-separated string
                lang_hints_str = getattr(self.settings, 'SONIOX_LANGUAGE_HINTS', 'ml,en')
                language_hints = [l.strip() for l in lang_hints_str.split(',')]
                
                # Batch provider (fallback)
                self.provider = SonioxSTTProvider(
                    api_key=api_key,
                    model=getattr(self.settings, 'SONIOX_MODEL', 'stt-rt-preview'),
                    language_hints=language_hints
                )
                
                # Streaming provider (faster!)
                if self.use_streaming:
                    try:
                        from src.services.speech.providers.soniox_streaming_provider import SonioxStreamingProvider
                        
                        self.streaming_provider = SonioxStreamingProvider(
                            api_key=api_key,
                            model=getattr(self.settings, 'SONIOX_MODEL', 'stt-rt-preview'),
                            language_hints=language_hints,
                            enable_speaker_diarization=getattr(self.settings, 'SONIOX_SPEAKER_DIARIZATION', False),
                            enable_endpoint_detection=getattr(self.settings, 'SONIOX_ENDPOINT_DETECTION', True)
                        )
                        self.logger.info(f"🚀 Soniox STREAMING provider initialized")
                    except Exception as stream_err:
                        self.logger.warning(f"⚠️ Soniox streaming init failed: {stream_err}. Using batch mode.")
                        self.use_streaming = False
                
                self.logger.info(f"🎙️ Soniox provider initialized (Malayalam + multilingual support)")
            except Exception as e:
                self.logger.warning(f"⚠️ Soniox init failed: {e}. Falling back to Google.")
                self.provider_name = "google"
                self.provider = GoogleSTTProvider(default_language=getattr(self.settings, "STT_LANGUAGE", "ml-IN"))
        
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
        from src.utils.latency import tracker
        try:
            self.logger.info("🎯 Ready to listen...")
            tracker.track("stt_listening_start")
            
            audio_bytes = None
            
            # 1. Try Memory/Stream capture first (SoundDevice) - FASTER
            try:
                # Collect all chunks from the async generator
                chunks = []
                async for chunk in self.audio_capture.stream_audio(
                    chunk_duration_ms=30,
                    timeout=timeout,
                    silence_duration=0.7, # Balanced for natural pauses
                    min_speech_duration=0.3  # Quick response
                ):
                    chunks.append(chunk)
                
                if chunks:
                    audio_bytes = b''.join(chunks)
                    
            except Exception as e:
                self.logger.warning(f"⚠️ SoundDevice capture failed ({e}). Falling back to Parecord.")
            
            # 2. Fallback to parecord (subprocess) if stream failed or returned no data
            if not audio_bytes:
                loop = asyncio.get_event_loop()
                audio_bytes = await loop.run_in_executor(
                    None,
                    lambda: self.audio_capture.record(
                        timeout=timeout,
                        silence_duration=0.5, 
                        min_speech_duration=0.5
                    )
                )
            
            if not audio_bytes:
                return None

            tracker.track("stt_audio_captured", f"Bytes: {len(audio_bytes)}")

            # Transcribe via provider
            assert self.provider is not None, "STT provider not initialized"
            result: STTResult = await self.provider.transcribe(audio_bytes)
            self.last_detected_language = result.language

            if result.text:
                tracker.track("stt_final_transcript", f"Text: {result.text}")
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
        
        Args:
            timeout: Maximum time to wait for speech (seconds)
        """
        # Only works with streaming provider
        if not self.streaming_provider:
            self.logger.warning("⚠️ Streaming not available, falling back to batch mode")
            return await self.listen(timeout)
        
        try:
            self.logger.info("🚀 Starting streaming listen (Fast Mode)...")
            from src.utils.latency import tracker
            tracker.track("stt_listening_start", "Streaming")
            
            # Start async audio stream with 30ms chunks for VAD and fast response
            audio_stream = self.audio_capture.stream_audio(
                chunk_duration_ms=30, # Match VAD
                timeout=timeout,
                silence_duration=0.7, # Balanced for natural pauses
                min_speech_duration=0.3
            )
            
            # Stream to Deepgram and collect results
            final_text = None
            partial_text = ""
            
            print("🔴 Listening (Stream)...")
            
            async for result in self.streaming_provider.stream_transcribe(audio_stream):
                if result.is_final:
                    tracker.track("stt_final_transcript", f"Stream Final: {result.text}")
                    final_text = result.text
                    self.last_detected_language = result.language
                    print(f"\r✅ Final: {final_text}                                ")
                else:
                    # Show partial results (optional)
                    if result.text != partial_text:
                        partial_text = result.text
                        # Overwrite line
                        print(f"\r⚡ {partial_text}...", end="", flush=True)
            
            if final_text:
                return final_text
            else:
                self.logger.warning("⚠️ No final transcript received")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Streaming listen error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to batch mode
            self.logger.info("🔄 Falling back to batch mode...")
            return await self.listen(timeout)

    def get_last_language(self) -> Optional[str]:
        """Get the language detected in the last transcription"""
        return self.last_detected_language

    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧽 Cleaning up speech recognizer...")
        if hasattr(self, 'audio_capture'):
            self.audio_capture.request_stop()
        # AudioCapture and providers will be garbage collected
